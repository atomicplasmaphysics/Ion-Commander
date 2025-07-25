#define _CRT_SECURE_NO_WARNINGS






// 
// 
// 
//    PLEASE CONSIDER THIS FILE AS A BLACK BOX.
// 
//       Only modify the code in lmf2txt.cpp
// 







#include "LMF_IO.h"

#ifndef LINUX
#define WINVER 0x0501
#pragma warning(disable : 4996)
#endif

#define LMF_IO_CLASS_VERSION (2018)


#define DAQ_SOURCE_CODE		0x80000000
#define DAN_SOURCE_CODE		0x40000000
#define CCF_HISTORY_CODE	0x20000000



void MyFILE::seek(unsigned __int64 pos)
{
	__int32 rval = _fseeki64(file, pos, SEEK_SET);
	if (rval == 0) this->position = pos; else error = 1;


	/*
		if (pos < 1000000000) {
			f_stream.seekg((unsigned int)pos, std::ios::beg);
			this->position = pos;
			return;
		}

		unsigned __int64 real_pos = 0;
		f_stream.seekg(0, std::ios::beg);
		for (;;) {

	//		f_stream.seekg(1000000000,std::ios::cur);
			real_pos += 1000000000;
			__int64 diff = pos - real_pos;
			if (diff < 1000000000) break;
		}
		__int64 diff = pos - real_pos;
		__int32 diff1 = __int32(diff);
		f_stream.seekg(diff1,std::ios::cur);*/

}




/*
void MyFILE::seek_to_end()
{
	f_stream.seekg(0, std::ios::end);
}
*/





#define INT_MIN_ (-2147483647-1)




void LMF_IO::write_times(MyFILE* out_file, time_t _Starttime, time_t _Stoptime) {
	unsigned __int32 dummy;
	if (CTime_version_output > 2003) {
		dummy = INT_MIN_ + 10; *out_file << dummy;
		dummy = (unsigned __int32)_Starttime; *out_file << dummy;
		dummy = 0;			*out_file << dummy;
		dummy = INT_MIN_ + 10;	*out_file << dummy;
		dummy = (unsigned __int32)_Stoptime;	*out_file << dummy;
		dummy = 0;			*out_file << dummy;
	}
	else {
		dummy = (unsigned __int32)_Starttime;	*out_file << dummy;
		dummy = (unsigned __int32)_Stoptime;	*out_file << dummy;
	}
}









unsigned __int32 ReadCStringLength(MyFILE& in_file)
{
	unsigned __int64 qwLength;
	unsigned __int32 dwLength;
	unsigned __int16 wLength;
	unsigned __int8  bLength;

	__int32 nCharSize = sizeof(__int8);

	// First, try to read a one-byte length
	in_file >> bLength;

	if (bLength < 0xff)
		return bLength;

	// Try a two-byte length
	in_file >> wLength;
	if (wLength == 0xfffe)
	{
		// Unicode string.  Start over at 1-byte length
		nCharSize = sizeof(wchar_t);

		in_file >> bLength;
		if (bLength < 0xff)
			return bLength;

		// Two-byte length
		in_file >> wLength;
		// Fall through to continue on same branch as ANSI string
	}
	if (wLength < 0xffff)
		return wLength;

	// 4-byte length
	in_file >> dwLength;
	if (dwLength < 0xffffffff)
		return dwLength;

	// 8-byte length
	in_file >> qwLength;

	return (unsigned __int32)qwLength;
}




void Read_CString_as_StdString(MyFILE& in_file, std::string& stdstring)
{
	__int32 length = ReadCStringLength(in_file);
	__int8* temp_string = new __int8[length + 1];
	in_file.read(temp_string, length);
	temp_string[length] = 0;
	stdstring = temp_string;
	delete[] temp_string;
	temp_string = 0;
}



void WriteCStringLength(MyFILE& out_file, unsigned __int32 nLength)
{
	unsigned __int8 dummy_uint8;
	unsigned __int16 dummy_uint16;
	unsigned __int32 dummy_uint32;
	unsigned __int64 dummy_uint64;

	if (nLength < 255)
	{
		dummy_uint8 = nLength; out_file << dummy_uint8;
	}
	else if (nLength < 0xfffe)
	{
		dummy_uint8 = 0xff; out_file << dummy_uint8;
		dummy_uint16 = nLength; out_file << dummy_uint16;
	}
	else if (nLength < 0xffffffff)
	{
		dummy_uint8 = 0xff; out_file << dummy_uint8;
		dummy_uint16 = 0xffff; out_file << dummy_uint16;
		dummy_uint32 = nLength; out_file << dummy_uint32;
	}
	else
	{
		dummy_uint8 = 0xff; out_file << dummy_uint8;
		dummy_uint16 = 0xffff; out_file << dummy_uint16;
		dummy_uint32 = 0xffffffff; out_file << dummy_uint32;
		dummy_uint64 = nLength; out_file << dummy_uint64;
	}
}



void Write_StdString_as_CString(MyFILE& out_file, std::string& stdstring)
{
	unsigned __int32 length = (unsigned __int32)(stdstring.length());
	WriteCStringLength(out_file, length);
	out_file.write(stdstring.c_str(), length);
}







/////////////////////////////////////////////////////////////////
__int32 LMF_IO::GetVersionNumber()
/////////////////////////////////////////////////////////////////
{
	return LMF_IO_CLASS_VERSION;
}











/////////////////////////////////////////////////////////////////
LMF_IO::LMF_IO(__int32 _num_channels, __int32 _num_ions)
/////////////////////////////////////////////////////////////////
{
	num_channels = _num_channels;
	num_ions = _num_ions;
	Initialize();
}






/////////////////////////////////////////////////////////////////
LMF_IO::~LMF_IO()
/////////////////////////////////////////////////////////////////
{
	if (InputFileIsOpen)  CloseInputLMF();
	if (OutputFileIsOpen) CloseOutputLMF();
	if (CAMAC_Data) { delete[] CAMAC_Data; CAMAC_Data = 0; }
	if (i32TDC) { delete[] i32TDC; i32TDC = 0; }
	if (us16TDC) { delete[] us16TDC; us16TDC = 0; }
	if (dTDC) { delete[] dTDC; dTDC = 0; }
	if (number_of_hits) { delete[] number_of_hits; number_of_hits = 0; }

	if (i64TDC) { delete[] i64TDC;		 i64TDC = 0; }
	if (i32ADCCounter) { delete[] i32ADCCounter; i32ADCCounter = 0; }
	if (i32ADCValue) { delete[] i32ADCValue;   i32ADCValue = 0; }

	for (__int32 i = 0; i < 3; ++i) {
		if (TDC8HP.TDC_info[i]) {
			if (TDC8HP.TDC_info[i]->INLCorrection) { delete[] TDC8HP.TDC_info[i]->INLCorrection;	TDC8HP.TDC_info[i]->INLCorrection = 0; }
			if (TDC8HP.TDC_info[i]->DNLData) { delete[] TDC8HP.TDC_info[i]->DNLData;			TDC8HP.TDC_info[i]->DNLData = 0; }
			if (TDC8HP.TDC_info[i]) { delete TDC8HP.TDC_info[i]; TDC8HP.TDC_info[i] = 0; }
		}
	}
	for (__int32 i = 0; i < 3; ++i) {
		if (TDC8HQ.TDC_info[i]) {
			if (TDC8HQ.TDC_info[i]->INLCorrection) { delete[] TDC8HQ.TDC_info[i]->INLCorrection;	TDC8HQ.TDC_info[i]->INLCorrection = 0; }
			if (TDC8HQ.TDC_info[i]->DNLData) { delete[] TDC8HQ.TDC_info[i]->DNLData;			TDC8HQ.TDC_info[i]->DNLData = 0; }
			if (TDC8HQ.TDC_info[i]) { delete TDC8HQ.TDC_info[i]; TDC8HQ.TDC_info[i] = 0; }
		}
	}
	if (ui32buffer) { delete[] ui32buffer; ui32buffer = 0; this->ui32buffer_size = 0; }



	if (CCFHistory_strings) {
		for (__int32 i = 0; i < number_of_CCFHistory_strings; ++i) {
			if (CCFHistory_strings[i]) { delete CCFHistory_strings[i]; CCFHistory_strings[i] = 0; }
		}
		delete[] CCFHistory_strings; CCFHistory_strings = 0;
	}
	if (DAQ_source_strings) {
		for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
			if (DAQ_source_strings[i]) { delete DAQ_source_strings[i]; DAQ_source_strings[i] = 0; }
		}
		delete[] DAQ_source_strings; DAQ_source_strings = 0;
	}
	if (DAN_source_strings) {
		for (__int32 i = 0; i < number_of_DAN_source_strings; ++i) {
			if (DAN_source_strings[i]) { delete DAN_source_strings[i]; DAN_source_strings[i] = 0; }
		}
		delete[] DAN_source_strings; DAN_source_strings = 0;
	}

	if (CCFHistory_strings_output) {
		for (__int32 i = 0; i < number_of_CCFHistory_strings_output; ++i) {
			if (CCFHistory_strings_output[i]) {
				delete CCFHistory_strings_output[i];
				CCFHistory_strings_output[i] = 0;
			}
		}
		delete[] CCFHistory_strings_output; CCFHistory_strings_output = 0;
	}
	if (DAQ_source_strings_output) {
		for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
			if (DAQ_source_strings_output[i]) { delete DAQ_source_strings_output[i]; DAQ_source_strings_output[i] = 0; }
		}
		delete[] DAQ_source_strings_output; DAQ_source_strings_output = 0;
	}
	if (DAN_source_strings_output) {
		for (__int32 i = 0; i < number_of_DAN_source_strings_output; ++i) {
			if (DAN_source_strings_output[i]) { delete DAN_source_strings_output[i]; DAN_source_strings_output[i] = 0; }
		}
		delete[] DAN_source_strings_output; DAN_source_strings_output = 0;
	}

	if (Parameter) { delete[] Parameter; Parameter = 0; }
	if (Parameter_old) { delete[] Parameter_old; Parameter_old = 0; }
}





/////////////////////////////////////////////////////////////////
void LMF_IO::Initialize()
/////////////////////////////////////////////////////////////////
{
	Parameter = new double[10000];
	Parameter_old = new double[10000];
	uint64_LMF_EventCounter = -1;
	not_Cobold_LMF = false;
	errorflag = 0;
	iLMFcompression = 0;
	number_of_channels2 = 0;
	InputFileIsOpen = false;
	OutputFileIsOpen = false;
	SIMPLE_DAQ_ID_Orignial = 0;
	input_lmf = 0;
	output_lmf = 0;
	DAQ_ID = 0;
	frequency = 1.;
	common_mode = 0;
	timerange = 0;
	must_read_first = true;
	uint64_number_of_read_events = 0;
	uint64_number_of_written_events = 0;
	number_of_channels_output = 0;
	number_of_channels2_output = -1;
	number_of_channels = 0;
	max_number_of_hits = 0;
	max_number_of_hits_output = 0;
	max_number_of_hits2_output = -1;
	data_format_in_userheader_output = -2;
	output_byte_counter = 0;
	timestamp_format = 0;
	timestamp_format_output = -1;
	DOUBLE_timestamp = 0.;
	ui64_timestamp = 0;
	skip_header = false;
	time_reference_output = 0;
	system_timeout_output = -1;
	Numberofcoordinates = -2;
	Numberofcoordinates_output = -2;
	DAQ_ID_output = 0;
	User_header_size_output = 0;
	CAMAC_Data = 0;
	changed_mask_read = 0;
	tdcresolution_output = -1.;
	tdcresolution = 0.;
	TDC8HP.SyncValidationChannel = 0;
	TDC8HP.exotic_file_type = 0;
	User_header_size = 0;
	TDC8HP.UserHeaderVersion = 7; // 4 = Cobold 2008 first release in 2008
	// 5 = Cobold 2008 R2 in August 2009
	// 6 = Cobold 2009?
	// 7 = Cobold 2011 R1 + R2

	HM1.use_normal_method = true;
	TDC8PCI2.use_normal_method_2nd_card = true;
	TDC8PCI2.use_normal_method = true;
	TDC8HP.VHR_25ps = true;
	common_mode_output = -1;
	DAQ_info = "";
	DAQ_info_Length = 0;
	Versionstring = "";
	FilePathName = "";
	OutputFilePathName = "";
	Comment = "";
	Comment_output = "";
	DAQ_info = "";
	Camac_CIF = "";
	TDC8HP.variable_event_length = 0;
	DAQVersion_output = -1;
	LMF_Version = -1;
	LMF_Version_output = -1;
	TDC8HP.csConfigFile = "";
	TDC8HP.csINLFile = "";
	TDC8HP.csDNLFile = "";
	TDC8HP.GroupingEnable_p66 = false;
	TDC8HP.GroupingEnable_p66_output = false;

	DAQ_SOURCE_CODE_bitmasked = 0;
	DAN_SOURCE_CODE_bitmasked = 0;
	CCF_HISTORY_CODE_bitmasked = 0;
	number_of_CCFHistory_strings = 0;
	number_of_DAN_source_strings = 0;
	number_of_DAQ_source_strings = 0;
	number_of_CCFHistory_strings_output = 0;
	number_of_DAN_source_strings_output = 0;
	number_of_DAQ_source_strings_output = 0;
	CCFHistory_strings = 0;
	DAN_source_strings = 0;
	DAQ_source_strings = 0;
	CCFHistory_strings_output = 0;
	DAN_source_strings_output = 0;
	DAQ_source_strings_output = 0;

	TDC8HP.number_of_bools = 0;
	TDC8HP.number_of_doubles = 0;
	TDC8HP.number_of_doubles = 0;

	TDC8PCI2.variable_event_length = 0;
	TDC8PCI2.i32NumberOfDAQLoops = 1;

	i32TDC = new __int32[num_channels * num_ions];			memset(i32TDC, 0, num_channels * num_ions * 4);
	bIsFallingTDC = new bool[num_channels * num_ions];			memset(bIsFallingTDC, 0, num_channels * num_ions * sizeof(bool));
	us16TDC = new unsigned __int16[num_channels * num_ions];  memset(us16TDC, 0, num_channels * num_ions * 2);
	dTDC = new double[num_channels * num_ions];			memset(dTDC, 0, num_channels * num_ions * 8);
	number_of_hits = new unsigned __int32[num_channels];			memset(number_of_hits, 0, num_channels * 4);
	i64TDC = new __int64[num_channels * num_ions];			memset(i64TDC, 0, num_channels * num_ions * 8);
	i32ADCCounter = new __int32[5 * num_ions];					memset(i32ADCCounter, 0, num_ions * 4);
	i32ADCValue = new __int32[5 * num_ions];					memset(i32ADCValue, 0, num_ions * 4);

	memset(number_of_hits, 0, num_channels * sizeof(__int32));

	TDC8HP.DMAEnable = true;
	TDC8HP.SSEEnable = false;
	TDC8HP.MMXEnable = true;
	TDC8HP.GroupTimeOut = 0.1;

	TDC8HP.channel_offset_for_rising_transitions = 0;

	//	TDC8HP.bdummy = false;
	//	TDC8HP.idummy = 0;
	//	TDC8HP.ddummy = 0.;

	TDC8HP.i32NumberOfDAQLoops = 1;
	TDC8HP.TDC8HP_DriverVersion = 0x00000000;
	TDC8HP.iTriggerChannelMask = 0;
	TDC8HP.iTime_zero_channel = 0;

	TDC8HP.Number_of_TDCs = 0;

	time_t osBinaryTime;
	time(&osBinaryTime);
	time_t time_dummy(osBinaryTime);
	Starttime = time_dummy;
	Stoptime = time_dummy;
	Starttime_output = 0;
	Stoptime_output = 0;
	CTime_version = 0;
	CTime_version_output = 0;
	number_of_DAQ_source_strings_output = -1;
	number_of_CCFHistory_strings_output = -1;
	number_of_DAN_source_strings_output = -1;

	number_of_bytes_in_PostEventData = 0;

	LMF_Header_version = 476759;
	ui64LevelInfo = 0;

	Cobold_Header_version = 2002;
	Cobold_Header_version_output = 0;

	TDC8HP.OffsetTimeZeroChannel_s = 0.;
	TDC8HP.BinsizeType = 0;

	for (__int32 i = 0; i < 3; ++i) {
		TDC8HP.TDC_info[i] = new TDC8HP_info_struct;
		TDC8HP.TDC_info[i]->INLCorrection = new __int32[8 * 1024];
		TDC8HP.TDC_info[i]->DNLData = new unsigned __int16[8 * 1024];
	}

	for (__int32 i = 0; i < 3; ++i) {
		TDC8HQ.TDC_info[i] = new TDC8HP_info_struct;
		TDC8HQ.TDC_info[i]->INLCorrection = new __int32[8 * 1024];
		TDC8HQ.TDC_info[i]->DNLData = new unsigned __int16[8 * 1024];
	}



	fADC8.driver_version = 0;
	fADC8.bReadCustomData = false;
	fADC8.i32NumberOfDAQLoops = 0;
	fADC8.number_of_bools = 0;
	fADC8.number_of_int32s = 0;
	fADC8.number_of_uint32s = 0;
	fADC8.number_of_doubles = 0;
	fADC8.GroupEndMarker = 0;
	fADC8.i32NumberOfADCmodules = 0;
	fADC8.iEnableGroupMode = 1;
	fADC8.iTriggerChannel = 0;
	fADC8.iPreSamplings_in_4800ps_units = 0;
	fADC8.iPostSamplings_in_9600ps_units = 0;
	fADC8.iEnableTDCinputs = 0;
	fADC8.veto_gate_length = 0;
	fADC8.veto_delay_length = 0;
	fADC8.veto_mask = 0;
	fADC8.dGroupRangeStart = 0.;
	fADC8.at_least_1_signal_was_written = false;
	fADC8.dGroupRangeEnd = 0.;
	for (__int32 mod = 0; mod < 8; mod++) {
		fADC8.firmware_version[mod] = 0;
		fADC8.serial_number[mod] = 0;
		for (__int32 ch = 0; ch < 8; ch++) {
			fADC8.GND_level[mod][ch] = 0;
			fADC8.iThreshold_GT[mod][ch] = 0;
			fADC8.iThreshold_LT[mod][ch] = 0;
		}
		fADC8.iChannelMode[mod][0] = fADC8.iChannelMode[mod][1] = 0;
		fADC8.iSynchronMode[mod][0] = fADC8.iSynchronMode[mod][1] = 0;
		fADC8.dSyncTimeOffset[mod][0] = fADC8.dSyncTimeOffset[mod][1] = 0.;
	}

	///////////////////////////////////


	fADC4.packet_count = -1;
	fADC4.number_of_bools = 0;
	fADC4.number_of_int32s = 0;
	fADC4.number_of_uint32s = 0;
	fADC4.number_of_doubles = 0;
	fADC4.GroupEndMarker = 12345678;
	fADC4.driver_version = 0;
	fADC4.i32NumberOfDAQLoops = 1;
	fADC4.bReadCustomData = true;
	fADC4.i32NumberOfADCmodules = 0;
	fADC4.iTriggerChannel = 0;
	fADC4.dGroupRangeStart = 0.;
	fADC4.dGroupRangeEnd = 0.;
	fADC4.csConfigFile = fADC4.csINLFile = fADC4.csDNLFile = "";
	for (__int32 i = 0; i < 20; i++) fADC4.bits_per_mVolt[i] = 0.;
	for (__int32 i = 0; i < 80; i++) fADC4.GND_level[i] = 0.;


	TDC8HQ.AllowOverlap_p67 = 0;
	TDC8HQ.UserHeaderVersion = 0;
	TDC8HQ.variable_event_length = 0;
	TDC8HQ.UseATC1 = 0;
	TDC8HQ.max_parameter_900_index = 0;
	TDC8HQ.number_of_bools = 0;
	TDC8HQ.number_of_int32s = 0;
	TDC8HQ.number_of_doubles = 0;
	TDC8HP.channel_offset_for_rising_transitions = 0;

	ui32buffer_size = 0;
	ui32buffer = 0;

	error_text[0] = (char*)"no error";
	error_text[1] = (char*)"error reading timestamp";
	error_text[2] = (char*)"error reading data";
	error_text[3] = (char*)"input file is already open";
	error_text[4] = (char*)"could not open input file";
	error_text[5] = (char*)"could not connect CAchrive to input file";
	error_text[6] = (char*)"error reading header";
	error_text[7] = (char*)"LMF not data of TDC8PCI2 or 2TDC8PCI2 or TDC8HP or CAMAC";
	error_text[8] = (char*)"file format not supported (only unsigned __int16 16bit and signed integer 32)";
	error_text[9] = (char*)"input file not open";
	error_text[10] = (char*)"output file not open";
	error_text[11] = (char*)"could not open output file";
	error_text[12] = (char*)"output file is already open";
	error_text[13] = (char*)"could not connect CAchrive to output file";
	error_text[14] = (char*)"some parameters are not initialized";
	error_text[15] = (char*)"CAMAC data tried to read with wrong function";
	error_text[16] = (char*)"seek does not work with non-fixed event lengths";
	error_text[17] = (char*)"writing file with non-fixed event length dan DAQVersion < 2008 no possible";
	error_text[18] = (char*)"end of input file";
	error_text[19] = (char*)"more channels in file than specified at new LMF_IO()";
	error_text[20] = (char*)"more hits per channel in file than specified at new LMF_IO()";
	error_text[21] = (char*)"more bytes after event than are reserved in LMF_IO source code";
}






/////////////////////////////////////////////////////////////////
void LMF_IO::CloseInputLMF()
/////////////////////////////////////////////////////////////////
{
	if (input_lmf) { input_lmf->close(); delete input_lmf; input_lmf = 0; }
	InputFileIsOpen = false;
}







/////////////////////////////////////////////////////////////////
unsigned __int64 LMF_IO::GetLastLevelInfo()
/////////////////////////////////////////////////////////////////
{
	return ui64LevelInfo;
}








/////////////////////////////////////////////////////////////////
bool LMF_IO::OpenNonCoboldFile(void)
/////////////////////////////////////////////////////////////////
{
	input_lmf->seek(0);

	if (skip_header) {
		DAQ_ID = DAQ_ID_RAW32BIT;
		data_format_in_userheader = 10;
		return true;
	}

	if (DAQ_ID == DAQ_ID_RAW32BIT) return true;

	DAQ_ID = DAQ_ID_SIMPLE;

	*input_lmf >> SIMPLE_DAQ_ID_Orignial;
	unsigned tempi;
	*input_lmf >> tempi; uint64_Numberofevents = tempi;
	*input_lmf >> data_format_in_userheader;

	User_header_size = 3 * sizeof(__int32);
	Headersize = 0;

	return true;
}








/////////////////////////////////////////////////////////////////
bool LMF_IO::OpenInputLMF(std::string Filename)
/////////////////////////////////////////////////////////////////
{
	return OpenInputLMF((__int8*)Filename.c_str());
}







/////////////////////////////////////////////////////////////////
bool LMF_IO::OpenInputLMF(__int8* LMF_Filename)
/////////////////////////////////////////////////////////////////
{
	unsigned __int32	unsigned_int_Dummy;
	__int32				data_format_in_header;
	__int8				byte_Dummy;
	__int32				byte_counter;
	__int32             current_pos;

	if (Parameter) memset(Parameter, 0, 10000 * sizeof(double));
	if (Parameter_old) memset(Parameter_old, 0, 10000 * sizeof(double));
	for (__int32 i = 901; i <= 932; i++) Parameter_old[i] = -1.e201;

	if (InputFileIsOpen) {
		errorflag = 3; // file is already open
		return false;
	}
	input_lmf = new MyFILE(true);

	TDC8HP.UserHeaderVersion = 0; // yes, 0 is ok here and 2 in LMF_IO::initialization is also ok

	input_lmf->open(LMF_Filename);

	if (input_lmf->error) {
		errorflag = 4; // could not open file
		input_lmf = 0;
		return false;
	}

	//L10:

	//  READ LMF-HEADER
	ArchiveFlag = 0;

	*input_lmf >> ArchiveFlag;

	DAQ_SOURCE_CODE_bitmasked = ArchiveFlag & DAQ_SOURCE_CODE;
	DAN_SOURCE_CODE_bitmasked = ArchiveFlag & DAN_SOURCE_CODE;
	CCF_HISTORY_CODE_bitmasked = ArchiveFlag & CCF_HISTORY_CODE;

	ArchiveFlag = ArchiveFlag & 0x1fffffff;

	if (ArchiveFlag != 476758 && ArchiveFlag != 476759) { // is this not a Cobold list mode file?
		not_Cobold_LMF = true;
		if (!OpenNonCoboldFile()) return false;
		errorflag = 0; // no error
		InputFileIsOpen = true;
		return true;
	}

	if (ArchiveFlag == 476758) Cobold_Header_version = 2002;
	if (ArchiveFlag == 476759) Cobold_Header_version = 2008;

	*input_lmf >> data_format_in_header;

	data_format_in_userheader = data_format_in_header;
	if (data_format_in_header != LM_USERDEF && data_format_in_header != LM_SHORT && data_format_in_header != LM_SLONG && data_format_in_header != LM_DOUBLE && data_format_in_header != LM_CAMAC) {
		errorflag = 8;
		CloseInputLMF();
		return false;
	}

	if (Cobold_Header_version <= 2002)	*input_lmf >> Numberofcoordinates;
	if (Cobold_Header_version >= 2008) {
		unsigned __int64 temp;
		*input_lmf >> temp;
		Numberofcoordinates = __int32(temp);
	}

	if (Numberofcoordinates >= 0) CAMAC_Data = new unsigned __int32[Numberofcoordinates];

	if (Cobold_Header_version <= 2002)	*input_lmf >> Headersize;
	if (Cobold_Header_version >= 2008) {
		unsigned __int64 temp;
		*input_lmf >> temp;
		Headersize = __int32(temp);
	}


	if (Cobold_Header_version <= 2002)	*input_lmf >> User_header_size;
	if (Cobold_Header_version >= 2008) {
		unsigned __int64 temp;
		*input_lmf >> temp;
		User_header_size = __int32(temp);
	}

	if (skip_header) {
		__int32 backstep;
		if (Cobold_Header_version <= 2002) backstep = sizeof(__int32) * 5;
		if (Cobold_Header_version >= 2008) backstep = sizeof(__int32) * 2 + sizeof(__int64) * 3;
		for (unsigned __int32 i = 0; i < Headersize - backstep; ++i) *input_lmf >> byte_Dummy;
		for (unsigned __int32 i = 0; i < User_header_size; ++i) *input_lmf >> byte_Dummy;
		errorflag = 0; // no error
		InputFileIsOpen = true;
		goto L666;
	}

	if (Cobold_Header_version >= 2008) *input_lmf >> uint64_Numberofevents;
	if (Cobold_Header_version <= 2002) {
		__int32 temp;
		*input_lmf >> temp;
		uint64_Numberofevents = temp;
	}

	// get CTime version:
	if (!CTime_version) {
		unsigned __int32 dummy_uint32;
		unsigned __int64 pos = (unsigned __int64)(input_lmf->tell());
		*input_lmf >> dummy_uint32;
		if (dummy_uint32 == INT_MIN_ + 10) CTime_version = 2005; else CTime_version = 2003;
		input_lmf->seek(pos);
	}

	CTime_version_output = CTime_version;

	unsigned __int32 dummy_uint32;
	if (CTime_version >= 2005) {
		*input_lmf >> dummy_uint32;
		*input_lmf >> dummy_uint32; Starttime = dummy_uint32;
		*input_lmf >> dummy_uint32;
	}
	else { *input_lmf >> dummy_uint32; Starttime = dummy_uint32; }

	if (CTime_version >= 2005) {
		*input_lmf >> dummy_uint32;
		*input_lmf >> dummy_uint32; Stoptime = dummy_uint32;
		*input_lmf >> dummy_uint32;
	}
	else {
		*input_lmf >> dummy_uint32; Stoptime = dummy_uint32;
	}

	Read_CString_as_StdString(*input_lmf, Versionstring);
	Read_CString_as_StdString(*input_lmf, FilePathName);
	Read_CString_as_StdString(*input_lmf, Comment);
	Comment_output = Comment;

	current_pos = __int32(input_lmf->tell());

	byte_counter = 0;

	if (CCF_HISTORY_CODE_bitmasked) {
		*input_lmf >> number_of_CCFHistory_strings;
		CCFHistory_strings = new std::string * [number_of_CCFHistory_strings];
		memset(CCFHistory_strings, 0, sizeof(std::string*) * number_of_CCFHistory_strings);
		for (__int32 i = 0; i < number_of_CCFHistory_strings; ++i) {
			__int32 string_len;
			*input_lmf >> string_len;
			CCFHistory_strings[i] = new std::string();
			CCFHistory_strings[i]->reserve(string_len);
			while (string_len > 0) {
				__int8 c;
				*input_lmf >> c;
				*CCFHistory_strings[i] += c;
				--string_len;
			}
		}
	}

	if (DAN_SOURCE_CODE_bitmasked) {
		*input_lmf >> number_of_DAN_source_strings;
		DAN_source_strings = new std::string * [number_of_DAN_source_strings];
		memset(DAN_source_strings, 0, sizeof(std::string*) * number_of_DAN_source_strings);
		for (__int32 i = 0; i < number_of_DAN_source_strings; ++i) {
			__int32 string_len;
			*input_lmf >> string_len;
			DAN_source_strings[i] = new std::string();
			DAN_source_strings[i]->reserve(string_len);
			while (string_len > 0) {
				__int8 c;
				*input_lmf >> c;
				*DAN_source_strings[i] += c;
				--string_len;
			}
		}
	}



	if (User_header_size == 0) {
		errorflag = 6;
		InputFileIsOpen = false;
		goto L666;
	}

	current_pos = __int32(input_lmf->tell());
	if (current_pos != __int32(Headersize)) {
		errorflag = 6;
		InputFileIsOpen = false;
		goto L666;
	}



	//  READ USER-HEADER
	if (Cobold_Header_version >= 2008) {
		*input_lmf >> LMF_Header_version;   byte_counter += sizeof(__int32);
	}

	if (Cobold_Header_version <= 2002) { *input_lmf >> unsigned_int_Dummy;	byte_counter += sizeof(__int32); }

	if (Cobold_Header_version >= 2008) {
		unsigned __int64 temp;
		*input_lmf >> temp;	unsigned_int_Dummy = (unsigned __int32)(temp);
		byte_counter += sizeof(unsigned __int64);
	}


	if (unsigned_int_Dummy != User_header_size) {
		errorflag = 6; // error reading header
		CloseInputLMF();
		return false;
	}

	*input_lmf >> DAQVersion;	byte_counter += sizeof(__int32);	// Version is always 2nd value

	*input_lmf >> DAQ_ID;		byte_counter += sizeof(__int32);	// DAQ_ID is always 3ed value

	if (DAQ_ID == DAQ_ID_TDC8)		goto L100;
	if (DAQ_ID == DAQ_ID_2TDC8)		goto L100;
	if (DAQ_ID == DAQ_ID_TDC8HP)	goto L100;
	if (DAQ_ID == DAQ_ID_TDC8HPRAW)	goto L100;
	if (DAQ_ID == DAQ_ID_HM1)		goto L100;
	if (DAQ_ID == DAQ_ID_CAMAC)		goto L100;
	if (DAQ_ID == DAQ_ID_HM1_ABM)	goto L100;
	if (DAQ_ID == DAQ_ID_TCPIP)		goto L100;
	if (DAQ_ID == DAQ_ID_FADC8)		goto L100;
	if (DAQ_ID == DAQ_ID_FADC4)		goto L100;
	if (DAQ_ID == DAQ_ID_TDC4HM)	goto L100;
	if (DAQ_ID == DAQ_ID_TDC8HQ)	goto L100;

	errorflag = 7; // LMF not data of TDC8PCI2 or 2TDC8PCI2 or TDC8HP or CAMAC or HM1 or TCPIP
	CloseInputLMF();
	return false;

L100:
	if (DAQ_ID == DAQ_ID_TDC8)	 byte_counter += ReadTDC8PCI2Header();
	if (DAQ_ID == DAQ_ID_2TDC8)	 byte_counter += Read2TDC8PCI2Header();
	if (DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW) byte_counter += ReadTDC8HPHeader_LMFV_1_to_7(byte_counter);
	if (DAQ_ID == DAQ_ID_HM1 || DAQ_ID == DAQ_ID_HM1_ABM)     byte_counter += ReadHM1Header();
	if (DAQ_ID == DAQ_ID_CAMAC)  byte_counter += ReadCAMACHeader();
	if (DAQ_ID == DAQ_ID_TCPIP)  byte_counter += ReadTCPIPHeader();
	if (DAQ_ID == DAQ_ID_FADC8)  byte_counter += ReadfADC8Header();
	if (DAQ_ID == DAQ_ID_FADC4)  byte_counter += ReadfADC4Header_up_to_v11();
	if (DAQ_ID == DAQ_ID_TDC4HM) byte_counter += ReadTDC4HMHeader();
	if (DAQ_ID == DAQ_ID_TDC8HQ) byte_counter += ReadTDC8HQHeader();

	if ((__int32(User_header_size) != byte_counter) || (data_format_in_userheader != data_format_in_header)) {
		if (!(DAQ_ID == DAQ_ID_TDC8 && this->LMF_Version == 0x8)
			&& !(this->LMF_Version == 7 && (DAQ_ID == DAQ_ID_HM1 || DAQ_ID == DAQ_ID_HM1_ABM) && DAQVersion == 20080507 && User_header_size > 100000)) {
			errorflag = 6; // error reading header
			CloseInputLMF();
			return false;
		}
	}

	if (data_format_in_header != LM_USERDEF && data_format_in_userheader != LM_SHORT && data_format_in_userheader != LM_SLONG && data_format_in_userheader != LM_DOUBLE && data_format_in_userheader != LM_CAMAC) {
		errorflag = 6; // error reading header
		CloseInputLMF();
		return false;
	}

	errorflag = 0; // no error
	InputFileIsOpen = true;

L666:

	return true;
}












/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteTDC8PCI2Header()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;
	__int32 int_Dummy = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	int_Dummy = __int32(DAQ_info.length());
	*output_lmf << int_Dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	if ((DAQVersion_output >= 20020408 && TDC8PCI2.use_normal_method)) {
		*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);
	}

	if (LMF_Version_output >= 0x9) {
		if ((number_of_DAQ_source_strings_output < 0) || (!DAQ_source_strings_output)) number_of_DAQ_source_strings_output = 0;
		*output_lmf << number_of_DAQ_source_strings_output;  byte_counter += sizeof(__int32);

		for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
			unsigned __int32 unsigned_int_Dummy = (unsigned __int32)(DAQ_source_strings_output[i]->length());
			*output_lmf << unsigned_int_Dummy;   byte_counter += sizeof(__int32);
			output_lmf->write(DAQ_source_strings_output[i]->c_str(), __int32(DAQ_source_strings_output[i]->length()));
			byte_counter += (unsigned __int32)(DAQ_source_strings_output[i]->length());
		}
	}

	*output_lmf << system_timeout_output; byte_counter += sizeof(__int32);		//   system time-out
	*output_lmf << time_reference_output; byte_counter += sizeof(__int32);
	*output_lmf << common_mode_output; byte_counter += sizeof(__int32);		//   0 common start    1 common stop
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	if (DAQVersion_output >= 20020408 && TDC8PCI2.use_normal_method) { *output_lmf << TDCDataType; byte_counter += sizeof(__int32); }
	*output_lmf << timerange; byte_counter += sizeof(__int32);	// time range of the tdc in microseconds

	if (DAQVersion_output < 20080507) {
		*output_lmf << number_of_channels_output; byte_counter += sizeof(__int32);			// number of channels
		*output_lmf << max_number_of_hits_output; byte_counter += sizeof(__int32);			// number of hits
	}
	else {
		__int64 i64_temp = number_of_channels_output;
		*output_lmf << i64_temp; byte_counter += sizeof(__int64);			// number of channels
		i64_temp = max_number_of_hits_output;
		*output_lmf << i64_temp; byte_counter += sizeof(__int64);			// number of hits
	}

	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	*output_lmf << module_2nd;	byte_counter += sizeof(__int32);	// indicator for 2nd module data

	if (DAQVersion_output >= 20020408 && TDC8PCI2.use_normal_method && (DAQ_ID_output == DAQ_ID_TDC8)) {
		*output_lmf << TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
		*output_lmf << TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
		*output_lmf << TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
		*output_lmf << TDC8PCI2.TriggerFalling_1st_card;	byte_counter += sizeof(__int32); // trigger falling edge 1st card
		*output_lmf << TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card
		*output_lmf << TDC8PCI2.EmptyCounter_1st_card;		byte_counter += sizeof(__int32); // EmptyCounter 1st card
		*output_lmf << TDC8PCI2.EmptyCounter_since_last_Event_1st_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 1st card
	}

	if (LMF_Version_output >= 10) {
		*output_lmf << TDC8PCI2.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	}

	return byte_counter;
}




















/////////////////////////////////////////////////////////////////
void LMF_IO::CloseOutputLMF()
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf) return;

	if (DAQ_ID_output == DAQ_ID_RAW32BIT) {
		output_lmf->close(); delete output_lmf; output_lmf = 0;
		OutputFileIsOpen = false;
		return;
	}

	if (Cobold_Header_version_output == 0) Cobold_Header_version_output = Cobold_Header_version;

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		output_lmf->seek(0);

		*output_lmf << SIMPLE_DAQ_ID_Orignial;
		unsigned __int32 dummy = __int32(uint64_number_of_written_events);
		*output_lmf << dummy;
		*output_lmf << data_format_in_userheader_output;

		output_lmf->close(); delete output_lmf; output_lmf = 0;
		OutputFileIsOpen = false;
		return;
	}

	//	if (out_ar) {
	output_lmf->seek(0);

	WriteFirstHeader();

	output_lmf->flush();
	Headersize_output = (unsigned __int32)(output_lmf->tell());
	unsigned __int64 seek_value;
	if (Cobold_Header_version_output <= 2002) seek_value = 3 * sizeof(unsigned __int32);
	if (Cobold_Header_version_output >= 2008) seek_value = 2 * sizeof(unsigned __int32) + sizeof(unsigned __int64);

	output_lmf->seek(seek_value);
	if (Cobold_Header_version_output <= 2002) *output_lmf << Headersize_output;
	if (Cobold_Header_version_output >= 2008) {
		unsigned __int64 temp = Headersize_output;
		*output_lmf << temp;
	}
	output_lmf->flush();
	output_lmf->seek(Headersize_output);

	if (Cobold_Header_version_output >= 2008 || DAQVersion_output >= 20080000) {
		*output_lmf << LMF_Header_version;
	}

	if (Cobold_Header_version_output <= 2002) *output_lmf << User_header_size_output;
	if (Cobold_Header_version_output >= 2008) {
		unsigned __int64 temp = User_header_size_output;
		*output_lmf << temp;
	}

	//out_ar->Close(); out_ar=0;
//	}

	if (output_lmf) { output_lmf->close(); delete output_lmf; output_lmf = 0; }
	OutputFileIsOpen = false;
}











/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC8PCI2Header()
/////////////////////////////////////////////////////////////////
{
	__int32 byte_counter;
	byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	//	input_lmf->flush();
	unsigned __int64 StartPosition = input_lmf->tell();
	__int32 old_byte_counter = byte_counter;
L50:
	byte_counter = old_byte_counter;

	//	TRY
	if (DAQVersion >= 20020408 && TDC8PCI2.use_normal_method) {
		*input_lmf >> LMF_Version;
		byte_counter += sizeof(__int32);
	}

	if (DAQVersion >= 20080507) {
		if (LMF_Version >= 0x8 && data_format_in_userheader == -1) TDC8PCI2.variable_event_length = 1;
		if (LMF_Version >= 0x8) {
			*input_lmf >> number_of_DAQ_source_strings;    byte_counter += sizeof(__int32);
			DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
			memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
			for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
				__int32 string_len;
				*input_lmf >> string_len;    byte_counter += sizeof(__int32);
				DAQ_source_strings[i] = new std::string();
				DAQ_source_strings[i]->reserve(string_len);
				while (string_len > 0) {
					__int8 c;
					*input_lmf >> c;     byte_counter += sizeof(__int8);
					*DAQ_source_strings[i] += c;
					--string_len;
				}
			}
		}
	}

	*input_lmf >> system_timeout;	byte_counter += sizeof(__int32);		//   system time-out
	*input_lmf >> time_reference;	byte_counter += sizeof(__int32);
	*input_lmf >> common_mode;		byte_counter += sizeof(__int32);			//   0 common start    1 common stop
	*input_lmf >> tdcresolution;	byte_counter += sizeof(double);	// tdc resolution in ns


	TDCDataType = 1;
	if (DAQVersion >= 20020408 && TDC8PCI2.use_normal_method) {
		*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);
	}
	*input_lmf >> timerange; byte_counter += sizeof(__int32);			// time range of the tdc in microseconds

	if (this->DAQVersion < 20080507) {
		*input_lmf >> number_of_channels; byte_counter += sizeof(__int32);	// number of channels
		*input_lmf >> max_number_of_hits; byte_counter += sizeof(__int32);	// number of hits
	}
	else {
		__int64 i64_temp;
		*input_lmf >> i64_temp; number_of_channels = (unsigned __int32)(i64_temp); byte_counter += sizeof(__int64);	// number of channels
		*input_lmf >> i64_temp; max_number_of_hits = (unsigned __int32)(i64_temp); byte_counter += sizeof(__int64);	// number of hits
	}

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }
	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	*input_lmf >> module_2nd;	byte_counter += sizeof(__int32);		// indicator for 2nd module data

	if (byte_counter == __int32(User_header_size - 12)) return byte_counter;

	if (DAQVersion >= 20020408 && TDC8PCI2.use_normal_method) {
		*input_lmf >> TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
		*input_lmf >> TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
		*input_lmf >> TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
		*input_lmf >> TDC8PCI2.TriggerFalling_1st_card;		byte_counter += sizeof(__int32); // trigger falling edge 1st card
		*input_lmf >> TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card
		*input_lmf >> TDC8PCI2.EmptyCounter_1st_card;		byte_counter += sizeof(__int32); // EmptyCounter 1st card
		*input_lmf >> TDC8PCI2.EmptyCounter_since_last_Event_1st_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 1st card
	}

	/*
		CATCH( CArchiveException, e )
			if (!TDC8PCI2.use_normal_method) return 0;
			TDC8PCI2.use_normal_method = false;
			in_ar->Close(); delete in_ar; in_ar = 0;
			input_lmf->seek(StartPosition);
			in_ar = new CArchive(input_lmf,CArchive::load);
			goto L50;
		END_CATCH
	*/

	if (LMF_Version >= 10) {
		*input_lmf >> TDC8PCI2.i32NumberOfDAQLoops;
		byte_counter += sizeof(__int32);
	}

	if (byte_counter != __int32(User_header_size - 12) && DAQVersion < 20080507) {
		if (!TDC8PCI2.use_normal_method) return 0;
		TDC8PCI2.use_normal_method = false;
		input_lmf->seek(StartPosition);
		goto L50;
	}

	if (LMF_Version == 0x8) {
		input_lmf->flush();
		input_lmf->seek((unsigned __int64)(this->Headersize + this->User_header_size));
		input_lmf->flush();
	}

	return byte_counter;
}








/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadCAMACHeader()
/////////////////////////////////////////////////////////////////
{
	__int32 byte_counter;
	byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	*input_lmf >> Camac_CIF_Length;	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[Camac_CIF_Length + 1];
	input_lmf->read(__int8_temp, Camac_CIF_Length);
	__int8_temp[Camac_CIF_Length] = 0;
	Camac_CIF = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += Camac_CIF_Length;

	*input_lmf >> system_timeout; byte_counter += sizeof(__int32);		// system time-out
	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);		// data format (2=short integer)

	return byte_counter;
}





/////////////////////////////////////////////////////////////////
__int32	LMF_IO::Read2TDC8PCI2Header()
/////////////////////////////////////////////////////////////////
{
	unsigned __int64 StartPosition;
	__int32 old_byte_counter;
	bool desperate_mode;

	TDC8PCI2.variable_event_length = 0;
	__int32 byte_counter;
	byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
	*input_lmf >> system_timeout; byte_counter += sizeof(__int32);		// system time-out

	if (LMF_Version >= 9 && DAQVersion >= 20110208) {				// handle new CStringArray information
		unsigned __int32 ui32CStringCount = system_timeout;			// # of defined CStrings

		__int32 iDummy;
		__int8 cDummy;
		for (unsigned __int32 ui32Count = 0; ui32Count < ui32CStringCount; ui32Count++) {	// now read every CString
			*input_lmf >> iDummy; byte_counter += sizeof(__int32);					// how many characters to read
			for (unsigned __int32 ui32Count2 = 0; ui32Count2 < (unsigned int)iDummy; ui32Count2++)		// read character by character
				input_lmf->read(&cDummy, 1);							// skip over DAq-source code
			byte_counter += iDummy;
		}
		*input_lmf >> system_timeout; byte_counter += sizeof(__int32);		// again system time-out
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> common_mode; byte_counter += sizeof(__int32);			// 0 common start    1 common stop
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);	// tdc resolution in ns

	*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);
	*input_lmf >> timerange; byte_counter += sizeof(__int32);			// time range of the tdc in microseconds
	if (DAQVersion >= 20080507 && DAQVersion < 20110208) {
		TDC8PCI2.variable_event_length = 1;
		__int32 iDummy;
		unsigned __int64 i64temp;
		*input_lmf >> i64temp;		number_of_channels = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of channels
		*input_lmf >> i64temp;		max_number_of_hits = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of hits
		if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
		if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

		*input_lmf >> i64temp;		number_of_channels2 = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of channels2
		*input_lmf >> i64temp;		max_number_of_hits2 = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of hits2
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);

		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);

		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);		// Sync Mode    (parameter 60)
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);		// IO address 2 (parameter 61)
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);
		*input_lmf >> iDummy;			byte_counter += sizeof(__int32);

		goto L200;
	}

	if (DAQVersion >= 20110208) {
		TDC8PCI2.variable_event_length = 1;
		__int32 iDummy;
		unsigned __int64 i64temp;
		*input_lmf >> i64temp;		number_of_channels = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of channels
		*input_lmf >> i64temp;		max_number_of_hits = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of hits
		if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
		if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

		*input_lmf >> i64temp;		number_of_channels2 = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of channels2
		*input_lmf >> i64temp;		max_number_of_hits2 = __int32(i64temp);	byte_counter += sizeof(unsigned __int64);			// number of hits2

		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // indicator 2nd module

		*input_lmf >> iDummy;		byte_counter += sizeof(__int32);



		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // gate delay
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // gate open
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // write empty events
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // trigger at falling edge
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // trigger at rising edge
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32);
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32);

		*input_lmf >> iDummy;		byte_counter += sizeof(__int32);
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32);

		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // gate delay
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // gate open
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // write empty events
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // trigger at falling edge
		*input_lmf >> iDummy;		byte_counter += sizeof(__int32); // trigger at rising edge
		if (byte_counter < __int32(User_header_size) - 20) {
			*input_lmf >> iDummy;		byte_counter += sizeof(__int32);
			*input_lmf >> iDummy;		byte_counter += sizeof(__int32);
		}

		goto L200;
	}


	*input_lmf >> number_of_channels; byte_counter += sizeof(__int32);	// number of channels
	*input_lmf >> max_number_of_hits; byte_counter += sizeof(__int32);	// number of hits
	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }
	*input_lmf >> number_of_channels2; byte_counter += sizeof(__int32);	// number of channels2
	*input_lmf >> max_number_of_hits2; byte_counter += sizeof(__int32);	// number of hits2
	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	//	input_lmf->flush();
	StartPosition = input_lmf->tell();
	old_byte_counter = byte_counter;
	desperate_mode = false;
L50:
	byte_counter = old_byte_counter;

	//	TRY

	if (TDC8PCI2.use_normal_method_2nd_card) {
		if (DAQVersion >= 20020408) {
			*input_lmf >> TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
			*input_lmf >> TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
			*input_lmf >> TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
			*input_lmf >> TDC8PCI2.TriggerFalling_1st_card;		byte_counter += sizeof(__int32); // trigger falling edge 1st card
			*input_lmf >> TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card
			*input_lmf >> TDC8PCI2.EmptyCounter_1st_card;		byte_counter += sizeof(__int32); // EmptyCounter 1st card
			*input_lmf >> TDC8PCI2.EmptyCounter_since_last_Event_1st_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 1st card
		}
		*input_lmf >> TDC8PCI2.sync_test_on_off;			byte_counter += sizeof(__int32); // sync test on/off
		*input_lmf >> TDC8PCI2.io_address_2nd_card;			byte_counter += sizeof(__int32); // io address 2nd card
		*input_lmf >> TDC8PCI2.GateDelay_2nd_card;			byte_counter += sizeof(__int32); // gate delay 2nd card
		*input_lmf >> TDC8PCI2.OpenTime_2nd_card;			byte_counter += sizeof(__int32); // open time 2nd card
		*input_lmf >> TDC8PCI2.WriteEmptyEvents_2nd_card;	byte_counter += sizeof(__int32); // write empty events 2nd card
		*input_lmf >> TDC8PCI2.TriggerFallingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger falling edge 2nd card
		*input_lmf >> TDC8PCI2.TriggerRisingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger rising edge 2nd card
		*input_lmf >> TDC8PCI2.EmptyCounter_2nd_card;		byte_counter += sizeof(__int32); // EmptyCounter 2nd card
		*input_lmf >> TDC8PCI2.EmptyCounter_since_last_Event_2nd_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 2nd card
	}
	else {
		*input_lmf >> module_2nd;							byte_counter += sizeof(__int32);	// indicator for 2nd module data
		*input_lmf >> TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
		*input_lmf >> TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
		*input_lmf >> TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
		*input_lmf >> TDC8PCI2.TriggerFalling_1st_card;		byte_counter += sizeof(__int32); // trigger falling edge 1st card
		*input_lmf >> TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card

		*input_lmf >> TDC8PCI2.GateDelay_2nd_card;			byte_counter += sizeof(__int32); // gate delay 2nd card
		if (!desperate_mode) { // this is only a quick fix.
			*input_lmf >> TDC8PCI2.OpenTime_2nd_card;			byte_counter += sizeof(__int32); // open time 2nd card
			*input_lmf >> TDC8PCI2.WriteEmptyEvents_2nd_card;	byte_counter += sizeof(__int32); // write empty events 2nd card
			*input_lmf >> TDC8PCI2.TriggerFallingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger falling edge 2nd card
			*input_lmf >> TDC8PCI2.TriggerRisingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger rising edge 2nd card
		}
	}

	/*
		CATCH( CArchiveException, e )
			if (!TDC8PCI2.use_normal_method_2nd_card) return 0;
			TDC8PCI2.use_normal_method_2nd_card = false;
			in_ar->Close(); delete in_ar; in_ar = 0;
			input_lmf->seek(StartPosition);
			in_ar = new CArchive(input_lmf,CArchive::load);
			goto L50;
		END_CATCH
	*/

L200:

	if (DAQVersion < 20080507) {
		if (byte_counter != __int32(User_header_size - 12)) {
			if (desperate_mode) return 0;
			if (!TDC8PCI2.use_normal_method_2nd_card) {
				desperate_mode = true;
			}
			TDC8PCI2.use_normal_method_2nd_card = false;
			input_lmf->seek(StartPosition);
			goto L50;
		}
	}

	if (DAQVersion >= 20080507 && DAQVersion < 20110208) {
		if (byte_counter != __int32(User_header_size - 20)) {
			byte_counter = -1000; // XXX (this line is okay. I have put the XXX just to bring it to attention)
		}
	}

	return byte_counter;
}






/////////////////////////////////////////////////////////////////
bool LMF_IO::ReadNextfADC4packet(ndigo_packet* packet, bool& bEnd_of_group_detected, __int16* i16buffer, __int32 buffersize_in_16bit_words)
/////////////////////////////////////////////////////////////////
{
L100:
	if (input_lmf->eof || input_lmf->error) {
		errorflag = 18;
		return false;
	}
	bEnd_of_group_detected = false;
	if (fADC4.packet_count < 1) {
		if (this->LMF_Version > 11) {
			__int32 event_end_marker;
			*input_lmf >> event_end_marker;
			if (event_end_marker != fADC4.GroupEndMarker) {
				__int64 pos = input_lmf->get_position();
				input_lmf->seek(pos - 8);
				*input_lmf >> event_end_marker;
				if (event_end_marker != fADC4.GroupEndMarker && event_end_marker != 1234567) {
					errorflag = 2;
					return false;
				}
				event_end_marker = fADC4.GroupEndMarker;
			}
			if (input_lmf->eof || input_lmf->error) {
				errorflag = 18;
				return false;
			}
			*input_lmf >> ui64_timestamp;
		}
		else {
			ui64_timestamp = 0;
		}
		DOUBLE_timestamp = ui64_timestamp * 1.e-12; // convert to seconds
		*input_lmf >> fADC4.packet_count;
	}

	if (errorflag) return false;

	bool a_signal_was_read = false;
	while (fADC4.packet_count > 0) {
		a_signal_was_read = true;
		fADC4.packet_count--;

		*input_lmf >> packet->channel;
		*input_lmf >> packet->card;
		*input_lmf >> packet->type;
		*input_lmf >> packet->flags;
		*input_lmf >> packet->length;
		*input_lmf >> packet->timestamp;

		if (errorflag) return false;

		//if (packet->flags) continue;

		if (packet->card > 10) continue;

		if (packet->type == CRONO_PACKET_TYPE_16_BIT_SIGNED) {
			__int32 length = __int32(packet->length * 4) < buffersize_in_16bit_words ? packet->length * 4 : buffersize_in_16bit_words;
			input_lmf->read((char*)i16buffer, length * sizeof(__int16));
			if (errorflag) return false;
			for (unsigned __int32 k = 0; k < (packet->length * 4 - length); k++) {
				__int16 dummy16;
				*input_lmf >> dummy16;
				if (errorflag) return false;
			}
			packet->length = length >> 2;
		}

		if (packet->type != CRONO_PACKET_TYPE_16_BIT_SIGNED
			&& packet->type != CRONO_PACKET_TYPE_TDC_RISING
			&& packet->type != CRONO_PACKET_TYPE_TDC_FALLING
			&& packet->type != CRONO_PACKET_TYPE_TDC_DATA
			&& packet->type != CRONO_PACKET_TYPE_TIMESTAMP_ONLY) {
			continue;
		}

		if (fADC4.packet_count > 0) return true;
	}


	if (this->LMF_Version > 12) {
		unsigned __int32 changed_mask = 0;
		*input_lmf >> changed_mask;
		if (changed_mask)
		{
			for (__int32 i = 0; i < 32; i++)
			{
				if (!changed_mask) break;
				if (changed_mask & 0x1)
				{
					double double_temp;
					*input_lmf >> double_temp;
					Parameter[901 + i] = double_temp;
				}
				changed_mask >>= 1;
			}
		}
	}



	bEnd_of_group_detected = true;
	number_of_bytes_in_PostEventData = 0;

	if (fADC4.bReadCustomData) {
		*input_lmf >> number_of_bytes_in_PostEventData;
		if (number_of_bytes_in_PostEventData == 12345678) {
			unsigned __int64 pos = input_lmf->tell();
			input_lmf->seek(pos - 4);
			number_of_bytes_in_PostEventData = 0;
		}
		if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
			input_lmf->error = 21;
			return false;
		}
		if (number_of_bytes_in_PostEventData < 0) {
			input_lmf->error = 21;
			return false;
		}
		for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
			unsigned __int8 byte_dummy;
			*input_lmf >> byte_dummy;
			ui8_PostEventData[i] = byte_dummy;
		}
	}

	++uint64_number_of_read_events;
	uint64_LMF_EventCounter++;

	if (!a_signal_was_read)
		goto L100;

	return true;
}






/////////////////////////////////////////////////////////////////
bool LMF_IO::ReadNextfADC8Signal(fADC8_signal_info_struct& signal_info, bool& bEnd_of_group_detected, unsigned __int32* ui32buffer, __int32 buffersize_in_32bit_words)
/////////////////////////////////////////////////////////////////
{
	if (!input_lmf) {
		errorflag = 9;
		return false;
	}
	if (errorflag) return false;

	//L100:

	input_lmf->read((char*)(&signal_info), sizeof(signal_info));

	if (input_lmf->error) {
		if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
		return false;
	}

	if (signal_info.adc_channel == -1 && signal_info.ModuleIndex == -1) {
		goto L200;
	}

	if (signal_info.signal_type != 8) {
		__int32 leng = buffersize_in_32bit_words > signal_info.signallength_including_header_in_32bit_words ? signal_info.signallength_including_header_in_32bit_words : buffersize_in_32bit_words;
		input_lmf->read(ui32buffer, leng * 4);
		if (input_lmf->error) {
			if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
			return false;
		}
		if (leng < signal_info.signallength_including_header_in_32bit_words) {
			__int8 byte_dummy;
			for (__int32 i = 0; i < (signal_info.signallength_including_header_in_32bit_words - leng) * 4; i++) input_lmf->read(&byte_dummy, 1);
		}
	}


L200:

	__int32 header_word;
	*input_lmf >> header_word;

	if (header_word != 12345678 && header_word != 0) {
		errorflag = 2;
		return false;
	}

	if (header_word == fADC8.GroupEndMarker) { // end of group
		bEnd_of_group_detected = true;
		++uint64_number_of_read_events;
	}
	else bEnd_of_group_detected = false;

	if (bEnd_of_group_detected && fADC8.bReadCustomData) {
		*input_lmf >> number_of_bytes_in_PostEventData;
		if (input_lmf->error) {
			if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
			return false;
		}
		if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
			input_lmf->error = 21;
			return false;
		}
		for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
			unsigned __int8 byte_dummy;
			*input_lmf >> byte_dummy;
			ui8_PostEventData[i] = byte_dummy;
		}
	}

	if (input_lmf->error) {
		if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
		return false;
	}

	return true;
}





/////////////////////////////////////////////////////////////////
bool LMF_IO::WriteNextfADC8Signal(fADC8_signal_info_struct* signal_info, unsigned __int32* ui32buffer)
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return false;
	}
	if (fADC8.at_least_1_signal_was_written) *output_lmf << __int32(0);

	output_lmf->write((char*)(signal_info), sizeof(fADC8_signal_info_struct));

	if (signal_info->signal_type != 8) {
		output_lmf->write((char*)ui32buffer, signal_info->signallength_including_header_in_32bit_words * 4);
	}

	fADC8.at_least_1_signal_was_written = true;

	return true;
}




/////////////////////////////////////////////////////////////////
bool LMF_IO::WritefADC8EndGroupMarker()
/////////////////////////////////////////////////////////////////
{
	if (fADC8.at_least_1_signal_was_written) *output_lmf << __int32(12345678);

	if (fADC8.bReadCustomData) {
		*output_lmf << number_of_bytes_in_PostEventData;
		for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
			*output_lmf << ui8_PostEventData[i];
		}
	}

	fADC8.at_least_1_signal_was_written = false;
	++uint64_number_of_written_events;

	return true;
}







__int32	LMF_IO::ReadfADC8_header_LMFversion9()
{
	__int32 byte_counter = 0;
	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;	byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;		byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference;	byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution;	byte_counter += sizeof(double);					// tdc resolution in ns
	*input_lmf >> TDCDataType;		byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of channels
	number_of_channels = __int32(temp_uint64);

	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of hits
	max_number_of_hits = __int32(temp_uint64);

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)



	// bools
	__int32 counter = 0;
	*input_lmf >> fADC8.number_of_bools;		byte_counter += sizeof(__int32);
	for (__int32 i = counter; i < fADC8.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;				byte_counter += sizeof(bool);
	}


	// unsigned 32bit
	counter = 0;
	*input_lmf >> fADC8.number_of_uint32s;		byte_counter += sizeof(__int32);

	*input_lmf >> fADC8.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.i32NumberOfADCmodules;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iEnableGroupMode;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iTriggerChannel;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iPreSamplings_in_4800ps_units;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iPostSamplings_in_9600ps_units;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iEnableTDCinputs;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[0][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[0][1];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[1][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[1][1];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[2][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[2][1];		byte_counter += sizeof(__int32); counter++;
	for (__int32 i = counter; i < fADC8.number_of_uint32s; ++i) {
		unsigned __int32 uint_dummy;
		*input_lmf >> uint_dummy;				byte_counter += sizeof(unsigned __int32);
	}


	// signed 32bit
	counter = 0;
	*input_lmf >> fADC8.number_of_int32s;		byte_counter += sizeof(__int32);

	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*input_lmf >> fADC8.iThreshold_GT[imod][ich];  byte_counter += sizeof(__int32);  counter++;
		}
	}
	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*input_lmf >> fADC8.iThreshold_LT[imod][ich];  byte_counter += sizeof(__int32);  counter++;
		}
	}
	*input_lmf >> fADC8.iSynchronMode[0][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[0][1];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[1][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[1][1];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[2][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[2][1];	byte_counter += sizeof(__int32); counter++;


	for (__int32 i = counter; i < fADC8.number_of_int32s; ++i) {
		__int32 int_dummy;
		*input_lmf >> int_dummy;				byte_counter += sizeof(__int32);
	}

	// doubles
	counter = 0;
	*input_lmf >> fADC8.number_of_doubles;		byte_counter += sizeof(__int32);
	*input_lmf >> fADC8.dGroupRangeStart;		byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dGroupRangeEnd;			byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[0][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[0][1];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[1][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[1][1];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[2][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[2][1];	byte_counter += sizeof(double); counter++;

	for (__int32 i = counter; i < fADC8.number_of_doubles; ++i) {
		double double_dummy;
		*input_lmf >> double_dummy;				byte_counter += sizeof(double);
	}

	*input_lmf >> fADC8.GroupEndMarker;			byte_counter += sizeof(__int32); counter++;

	return byte_counter;
}







__int32	LMF_IO::ReadfADC8_header_LMFversion10()
{
	__int32 byte_counter = 0;
	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;	byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;	byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference;	byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution;	byte_counter += sizeof(double);		// tdc resolution in ns
	*input_lmf >> TDCDataType;		byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of channels
	number_of_channels = __int32(temp_uint64);

	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of hits
	max_number_of_hits = __int32(temp_uint64);

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)


	// bools
	__int32 counter = 0;
	*input_lmf >> fADC8.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = counter; i < fADC8.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;	byte_counter += sizeof(bool);
	}

	// unsigned 32bit
	counter = 0;
	*input_lmf >> fADC8.number_of_uint32s;		byte_counter += sizeof(__int32);

	*input_lmf >> fADC8.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.i32NumberOfADCmodules;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iEnableGroupMode;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iTriggerChannel;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iPreSamplings_in_4800ps_units;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iPostSamplings_in_9600ps_units;	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iEnableTDCinputs;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[0][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[0][1];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[1][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[1][1];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[2][0];		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iChannelMode[2][1];		byte_counter += sizeof(__int32); counter++;

	for (__int32 i = 0; i < 3; i++) {
		*input_lmf >> fADC8.firmware_version[i]; ; byte_counter += sizeof(__int32); counter++; // adc module firmware
		*input_lmf >> fADC8.serial_number[i]; ; byte_counter += sizeof(__int32); counter++; // adc module serial number
	}

	*input_lmf >> fADC8.driver_version; byte_counter += sizeof(__int32); counter++; // adc driver version number

	for (__int32 i = counter; i < fADC8.number_of_uint32s; ++i) {
		unsigned __int32 uint_dummy;
		*input_lmf >> uint_dummy;				byte_counter += sizeof(unsigned __int32);
	}

	// signed 32bit
	counter = 0;
	*input_lmf >> fADC8.number_of_int32s;		byte_counter += sizeof(__int32);

	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*input_lmf >> fADC8.iThreshold_GT[imod][ich];	byte_counter += sizeof(__int32);  counter++;
		}
	}
	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*input_lmf >> fADC8.iThreshold_LT[imod][ich];	byte_counter += sizeof(__int32);  counter++;
		}
	}
	*input_lmf >> fADC8.iSynchronMode[0][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[0][1];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[1][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[1][1];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[2][0];	byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.iSynchronMode[2][1];	byte_counter += sizeof(__int32); counter++;

	*input_lmf >> fADC8.GroupEndMarker;			byte_counter += sizeof(__int32); counter++;

	if (fADC8.GroupEndMarker != 12345678) return 0;

	*input_lmf >> fADC8.veto_gate_length;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.veto_delay_length;		byte_counter += sizeof(__int32); counter++;
	*input_lmf >> fADC8.veto_mask;				byte_counter += sizeof(__int32); counter++;

	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*input_lmf >> fADC8.GND_level[imod][ich]; byte_counter += sizeof(__int32); counter++;
		}
	}

	__int32 int_dummy;
	fADC8.bReadCustomData = false;
	if (counter < fADC8.number_of_int32s) {
		*input_lmf >> int_dummy;			byte_counter += sizeof(__int32);
		fADC8.bReadCustomData = int_dummy ? true : false;
		counter++;
	}
	iLMFcompression = 0;
	if (counter < fADC8.number_of_int32s) {
		*input_lmf >> iLMFcompression;			byte_counter += sizeof(__int32);
		counter++;
	}
	if (counter < fADC8.number_of_int32s) {
		for (__int32 i = counter; i < fADC8.number_of_int32s; ++i) {
			*input_lmf >> int_dummy;			byte_counter += sizeof(__int32);
			counter++;
		}
	}

	// doubles
	counter = 0;
	*input_lmf >> fADC8.number_of_doubles;		byte_counter += sizeof(__int32);
	*input_lmf >> fADC8.dGroupRangeStart;		byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dGroupRangeEnd;			byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[0][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[0][1];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[1][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[1][1];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[2][0];	byte_counter += sizeof(double); counter++;
	*input_lmf >> fADC8.dSyncTimeOffset[2][1];	byte_counter += sizeof(double); counter++;
	for (__int32 i = counter; i < fADC8.number_of_doubles; ++i) {
		double double_dummy;
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
	}

	*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
	if (int_dummy != 123456789) return 0;

	return byte_counter;
}















__int32	LMF_IO::WritefADC8_header_LMFversion10()
{
	unsigned __int32 unsigned_int_Dummy;

	__int32 byte_counter = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);			// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);

	if ((number_of_DAQ_source_strings_output < 0) || (!DAQ_source_strings_output)) number_of_DAQ_source_strings_output = 0;
	*output_lmf << number_of_DAQ_source_strings_output;  byte_counter += sizeof(__int32);

	for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
		unsigned_int_Dummy = (unsigned __int32)(DAQ_source_strings_output[i]->length());
		*output_lmf << unsigned_int_Dummy;   byte_counter += sizeof(__int32);
		output_lmf->write(DAQ_source_strings_output[i]->c_str(), __int32(DAQ_source_strings_output[i]->length()));
		byte_counter += (unsigned __int32)(DAQ_source_strings_output[i]->length());
	}

	*output_lmf << time_reference_output;	byte_counter += sizeof(__int32);
	*output_lmf << tdcresolution_output;	byte_counter += sizeof(double);		// tdc resolution in ns
	*output_lmf << TDCDataType;		byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64 = number_of_channels_output;
	*output_lmf << temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of channels

	temp_uint64 = max_number_of_hits;
	*output_lmf << temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of hits

	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	// bools
	__int32 counter = 0;
	*output_lmf << fADC8.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = counter; i < fADC8.number_of_bools; ++i) {
		bool bool_dummy = false;
		*output_lmf << bool_dummy;	byte_counter += sizeof(bool);
	}

	// unsigned 32bit
	counter = 0;
	*output_lmf << fADC8.number_of_uint32s;		byte_counter += sizeof(__int32);

	*output_lmf << fADC8.i32NumberOfDAQLoops;		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.i32NumberOfADCmodules;	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iEnableGroupMode;			byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iTriggerChannel;			byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iPreSamplings_in_4800ps_units;	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iPostSamplings_in_9600ps_units;	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iEnableTDCinputs;			byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[0][0];		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[0][1];		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[1][0];		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[1][1];		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[2][0];		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iChannelMode[2][1];		byte_counter += sizeof(__int32); counter++;

	for (__int32 i = 0; i < 3; i++) {
		*output_lmf << fADC8.firmware_version[i];	byte_counter += sizeof(__int32); counter++; // adc module firmware
		*output_lmf << fADC8.serial_number[i];		byte_counter += sizeof(__int32); counter++; // adc module serial number
	}

	*output_lmf << fADC8.driver_version; byte_counter += sizeof(__int32); counter++; // adc driver version number

	for (__int32 i = counter; i < fADC8.number_of_uint32s; ++i) {
		unsigned __int32 uint_dummy = 0;
		*output_lmf << uint_dummy;				byte_counter += sizeof(unsigned __int32);
	}

	// signed 32bit
	counter = 0;
	*output_lmf << fADC8.number_of_int32s;		byte_counter += sizeof(__int32);

	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*output_lmf << fADC8.iThreshold_GT[imod][ich];	byte_counter += sizeof(__int32);  counter++;
		}
	}
	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*output_lmf << fADC8.iThreshold_LT[imod][ich];	byte_counter += sizeof(__int32);  counter++;
		}
	}
	*output_lmf << fADC8.iSynchronMode[0][0];	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iSynchronMode[0][1];	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iSynchronMode[1][0];	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iSynchronMode[1][1];	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iSynchronMode[2][0];	byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.iSynchronMode[2][1];	byte_counter += sizeof(__int32); counter++;

	*output_lmf << fADC8.GroupEndMarker;			byte_counter += sizeof(__int32); counter++;

	*output_lmf << fADC8.veto_gate_length;		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.veto_delay_length;		byte_counter += sizeof(__int32); counter++;
	*output_lmf << fADC8.veto_mask;				byte_counter += sizeof(__int32); counter++;

	for (__int32 imod = 0; imod < 3; imod++) {
		for (__int32 ich = 0; ich < 8; ich++) {
			*output_lmf << fADC8.GND_level[imod][ich]; byte_counter += sizeof(__int32); counter++;
		}
	}

	if (counter < fADC8.number_of_int32s) {
		for (__int32 i = counter; i < fADC8.number_of_int32s; ++i) {
			*output_lmf << __int32(fADC8.bReadCustomData ? 1 : 0);	byte_counter += sizeof(__int32);
		}
	}

	// doubles
	counter = 0;
	*output_lmf << fADC8.number_of_doubles;		byte_counter += sizeof(__int32);
	*output_lmf << fADC8.dGroupRangeStart;			byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dGroupRangeEnd;			byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[0][0];	byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[0][1];	byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[1][0];	byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[1][1];	byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[2][0];	byte_counter += sizeof(double); counter++;
	*output_lmf << fADC8.dSyncTimeOffset[2][1];	byte_counter += sizeof(double); counter++;
	for (__int32 i = counter; i < fADC8.number_of_doubles; ++i) {
		double double_dummy = 0.;
		*output_lmf << double_dummy; byte_counter += sizeof(double);
	}

	__int32 int_dummy = 123456789;
	*output_lmf << int_dummy;	byte_counter += sizeof(__int32);

	return byte_counter;
}














/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadfADC8Header()
/////////////////////////////////////////////////////////////////
{
	__int32	byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);			// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);	// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	byte_counter += DAQ_info_Length;  // DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);

	if (LMF_Version == 10) byte_counter += ReadfADC8_header_LMFversion10();
	if (LMF_Version == 9)  byte_counter += ReadfADC8_header_LMFversion9();

	return byte_counter;
}










__int32	LMF_IO::ReadfADC4Header_up_to_v11()
{
	__int32 i32Dummy = 0;
	unsigned __int64 ui64Dummy = 0;
	double dDummy = 0.;
	bool bDummy = false;
	char cDummy = 0;

	__int32 byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);

	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;	byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;	byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference;	byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution;	byte_counter += sizeof(double);					// tdc resolution in ns
	*input_lmf >> TDCDataType;		byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of channels
	number_of_channels = __int32(temp_uint64);

	*input_lmf >> temp_uint64;		byte_counter += sizeof(unsigned __int64);		// number of hits
	max_number_of_hits = __int32(temp_uint64);

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	*input_lmf >> fADC4.i32NumberOfADCmodules;	byte_counter += sizeof(__int32);


	__int32 check_value;
	*input_lmf >> check_value; byte_counter += sizeof(__int32);

	if (check_value == 12345678) {
		for (__int32 i = 0; i < fADC4.i32NumberOfADCmodules; i++) {
			*input_lmf >> fADC4.ndigo_parameters[i].bandwidth;		byte_counter += sizeof(double);
			*input_lmf >> fADC4.ndigo_parameters[i].board_id;		byte_counter += sizeof(__int32);
			*input_lmf >> fADC4.ndigo_parameters[i].channel_mask;	byte_counter += sizeof(__int32);
			*input_lmf >> fADC4.ndigo_parameters[i].channels;		byte_counter += sizeof(__int32);
			*input_lmf >> fADC4.ndigo_parameters[i].sample_period;	byte_counter += sizeof(double);
			*input_lmf >> fADC4.ndigo_parameters[i].sample_rate;	byte_counter += sizeof(double);
			*input_lmf >> fADC4.ndigo_parameters[i].version;		byte_counter += sizeof(__int32);

			if (DAQVersion >= 20140617) { // DAQ_VERSION13FADC4
				ndigo_static_info* ndsi = &fADC4.ndigo_info[i];
				*input_lmf >> ndsi->size;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->version;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->board_id;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->driver_revision;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->firmware_revision;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->board_revision;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->board_configuration;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->adc_resolution;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->nominal_sample_rate;				byte_counter += sizeof(double);
				*input_lmf >> ndsi->analog_bandwidth;			byte_counter += sizeof(double);
				*input_lmf >> ndsi->chip_id;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->board_serial;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->flash_serial_low;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->flash_serial_high;			byte_counter += sizeof(__int32);
				*input_lmf >> ndsi->flash_valid;			byte_counter += sizeof(__int32);
				*input_lmf >> i32Dummy;			byte_counter += sizeof(__int32);
				ndsi->dc_coupled = (i32Dummy != 0) ? true : false;
				*input_lmf >> ndsi->subversion_revision;			byte_counter += sizeof(__int32);
				for (__int32 k = 0; k < 20; k++) {
					*input_lmf >> ndsi->calibration_date[k];			byte_counter += sizeof(__int8);
				}
			}
			else {
				memset(&fADC4.ndigo_info[i], 0, sizeof(ndigo_static_info));
			}

		}
	}
	else {
		unsigned __int64 pos = input_lmf->tell(); input_lmf->seek(pos - 4); byte_counter -= sizeof(__int32);
		for (__int32 i = 0; i < fADC4.i32NumberOfADCmodules; i++) {
			input_lmf->read((char*)&fADC4.ndigo_parameters[i], sizeof(ndigo_param_info)); byte_counter += sizeof(ndigo_param_info);
			__int32 size_diff = sizeof(ndigo_param_info) - fADC4.ndigo_parameters[i].size;
			if (size_diff) {
				pos = input_lmf->tell(); input_lmf->seek(pos - size_diff); byte_counter -= size_diff;
			}
		}

	}





	for (unsigned __int32 i = 0; i < number_of_channels; i++) {
		*input_lmf >> fADC4.threshold_GT[i];	byte_counter += sizeof(double);
		*input_lmf >> fADC4.threshold_LT[i];	byte_counter += sizeof(double);
	}

	for (unsigned __int32 i = 0; i < number_of_channels; i++) {
		*input_lmf >> fADC4.set_DC_offset[i];	byte_counter += sizeof(double);
	}

	memset(fADC4.GND_level, 0, 80 * sizeof(double));
	if (LMF_Version > 10) {
		for (unsigned __int32 i = 0; i < number_of_channels; i++) {
			*input_lmf >> fADC4.GND_level[i];	byte_counter += sizeof(double);
		}
	}

	__int32 num_temp = fADC4.i32NumberOfADCmodules < 4 ? 4 : fADC4.i32NumberOfADCmodules;
	for (__int32 i = 0; i < num_temp; i++) { // write ADC mode 4x1.25Gs or 2x2.5Gs or 1x5Gs)
		*input_lmf >> fADC4.sampling_mode[i];	byte_counter += sizeof(__int32);
	}

	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32); // precursor in steps of 3.2 ns
	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32); // length after end of signal in steps of 3.2 ns
	for (unsigned __int32 i = 2; i < number_of_channels; i++) {
		*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32); // read precursor and length for all other channels. Currently only for future use
		*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32);
	}

	*input_lmf >> ui64Dummy;	byte_counter += sizeof(__int64);				// ui64RisingEnable
	*input_lmf >> ui64Dummy;	byte_counter += sizeof(__int64);				// ui64FallingEnable
	*input_lmf >> i32Dummy;		byte_counter += sizeof(__int32);				// i32TriggerEdge
	*input_lmf >> fADC4.iTriggerChannel;	byte_counter += sizeof(__int32);	// i32TriggerChannel
	fADC4.iTriggerChannel--;

	*input_lmf >> bDummy;	byte_counter += sizeof(bool);					// bOutputLevel
	*input_lmf >> fADC4.dGroupRangeStart;	byte_counter += sizeof(double);	// dGroupRangeStart
	*input_lmf >> fADC4.dGroupRangeEnd;		byte_counter += sizeof(double);	// dGroupRangeEnd

	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32);				// read Config file
	fADC4.csConfigFile = "";
	for (__int32 i32Count = 0; i32Count < i32Dummy; i32Count++)
	{
		input_lmf->read(&cDummy, 1);	byte_counter += sizeof(char);
		fADC4.csConfigFile += cDummy;
	}
	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32);				// read INL file
	fADC4.csINLFile = "";
	for (__int32 i32Count = 0; i32Count < i32Dummy; i32Count++)
	{
		input_lmf->read(&cDummy, 1);	byte_counter += sizeof(char);
		fADC4.csINLFile += cDummy;
	}
	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32);				// read DNL file
	fADC4.csDNLFile = "";
	for (__int32 i32Count = 0; i32Count < i32Dummy; i32Count++)
	{
		input_lmf->read(&cDummy, 1);	byte_counter += sizeof(char);
		fADC4.csDNLFile += cDummy;
	}

	*input_lmf >> i32Dummy;	byte_counter += sizeof(__int32);	// dummy
	*input_lmf >> dDummy;	byte_counter += sizeof(double);		// dGroupTimeout

	// read TDCInfo
	*input_lmf >> TDC8HP.Number_of_TDCs;  byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*input_lmf >> TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*input_lmf >> TDC8HP.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->version;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*input_lmf >> TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}

	// now handle additional bools
	*input_lmf >> fADC4.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 0; i < fADC4.number_of_bools; ++i) {
		*input_lmf >> bDummy;	byte_counter += sizeof(bool);
	}


	// now handle additional 32Bit values (signed or unsigned)
	*input_lmf >> fADC4.number_of_int32s;		byte_counter += sizeof(__int32);
	if (fADC4.number_of_int32s == 3 && this->LMF_Version == 11) this->LMF_Version = 12; // dirty work around for old LMFs

	__int32 counter = fADC4.number_of_int32s;
	if (counter > 0) { *input_lmf >> fADC4.i32NumberOfDAQLoops;		counter--;	byte_counter += sizeof(__int32); }
	if (counter > 0) { *input_lmf >> TDC8HP.TDC8HP_DriverVersion;	counter--;	byte_counter += sizeof(__int32); }
	while (counter > 0) {
		*input_lmf >> i32Dummy;
		byte_counter += sizeof(__int32);
		counter--;
	}

	*input_lmf >> fADC4.number_of_doubles;		byte_counter += sizeof(__int32);
	counter = fADC4.number_of_doubles;
	if (LMF_Version > 10) {
		for (__int32 i = 0; i < fADC4.i32NumberOfADCmodules; i++) {
			*input_lmf >> fADC4.bits_per_mVolt[i];	byte_counter += sizeof(double);
			counter--;
		}
	}
	else {
		*input_lmf >> dDummy; byte_counter += sizeof(double);	counter--;
		for (__int32 i = 0; i < fADC4.i32NumberOfADCmodules; i++) fADC4.bits_per_mVolt[i] = dDummy;
	}
	while (counter > 0) { *input_lmf >> dDummy;	byte_counter += sizeof(double);	counter--; }

	*input_lmf >> i32Dummy;			byte_counter += sizeof(__int32);
	if (i32Dummy != 1234567) return 0;

	uint64_LMF_EventCounter = 0;

	return byte_counter;
}





/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC4HMHeader()
/////////////////////////////////////////////////////////////////
{
	__int32		byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;



	//	input_lmf->flush();
	//unsigned __int64 StartPosition = input_lmf->tell();
	__int32 old_byte_counter = byte_counter;

	byte_counter = old_byte_counter;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);


	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;    byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;     byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns
	*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;
	number_of_channels = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of channels

	*input_lmf >> temp_uint64;
	max_number_of_hits = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of hits

	if (__int32(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (__int32(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	if (data_format_in_userheader < -10) data_format_in_userheader = -1;

	bool	bool_dummy = false;
	__int64 i64_dummy = 0;
	__int32 i32_dummy = 0;
	double	d_dummy = 0.;

	*input_lmf >> bool_dummy; byte_counter += sizeof(bool);	// parameter 60-1

	*input_lmf >> i64_dummy;	byte_counter += sizeof(__int64);	// parameter 61-1
	*input_lmf >> i64_dummy;	byte_counter += sizeof(__int64);	// parameter 62-1
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 63-1
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 64-1

	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 65-1
	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 66-1
	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 67-1

	*input_lmf >> d_dummy;		byte_counter += sizeof(double);		// parameter 68-1

	*input_lmf >> TDC4HM.GroupRangeStart_p69;	byte_counter += sizeof(double);		// parameter 69-1
	*input_lmf >> TDC4HM.GroupRangeEnd_p70;		byte_counter += sizeof(double);		// parameter 70-1

	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 71-1
	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 72-1

	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 73-1
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 74-1
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 75-1
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);	// parameter 76-1

	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 80-1
	*input_lmf >> bool_dummy; 	byte_counter += sizeof(bool);	// parameter 81-1

	for (__int32 k = 0; k < 3; k++) {
		*input_lmf >> i32_dummy;
		byte_counter += sizeof(__int32);
		for (__int32 i = 0; i < i32_dummy; i++) {
			__int8 byte_dummy = 0;
			*input_lmf >> byte_dummy;
		}
		byte_counter += i32_dummy;
	}

	*input_lmf >> i32_dummy;		byte_counter += sizeof(__int32);
	*input_lmf >> bool_dummy;		byte_counter += sizeof(bool);
	*input_lmf >> d_dummy;			byte_counter += sizeof(double);
	*input_lmf >> bool_dummy;		byte_counter += sizeof(bool);
	*input_lmf >> bool_dummy;		byte_counter += sizeof(bool);
	*input_lmf >> bool_dummy;		byte_counter += sizeof(bool);

	//// read TDCInfo
	__int32 TDC_count = 0;
	*input_lmf >> TDC_count;		byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC_count; ++iCount) {
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy; 	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC4HM.resolution;		byte_counter += sizeof(double);
		*input_lmf >> TDC4HM.board_serial;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC4HM.version;			byte_counter += sizeof(__int32);
		*input_lmf >> i32_dummy;				byte_counter += sizeof(__int32);

		for (__int32 i = 0; i < 8 * 1024; i++) *input_lmf >> i32_dummy;
		byte_counter += 8 * 1024 * 4;
		for (__int32 i = 0; i < 4 * 1024; i++) *input_lmf >> i32_dummy;
		byte_counter += 4 * 1024 * 4;
		*input_lmf >> TDC4HM.flash_valid;			byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC4HM.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 0; i < TDC4HM.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;	byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC4HM.number_of_int32s; byte_counter += sizeof(__int32);
	*input_lmf >> TDC4HM.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC4HM.driver_revision;	byte_counter += sizeof(__int32);
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
	*input_lmf >> i32_dummy;	byte_counter += sizeof(__int32);
	for (__int32 i = 5; i < TDC8HP.number_of_int32s; ++i) {
		__int32 int_dummy;
		*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
	}

	*input_lmf >> TDC4HM.number_of_doubles; byte_counter += sizeof(__int32);
	*input_lmf >> d_dummy;					byte_counter += sizeof(double);

	for (__int32 i = 0; i < 5; i++) {
		*input_lmf >> TDC4HM.dc_offset[i]; byte_counter += sizeof(double);
	}
	*input_lmf >> TDC4HM.veto_start;		byte_counter += sizeof(double);
	*input_lmf >> TDC4HM.veto_end;			byte_counter += sizeof(double);
	*input_lmf >> TDC4HM.filter_mask_1;		byte_counter += sizeof(double);
	*input_lmf >> TDC4HM.filter_mask_2;		byte_counter += sizeof(double);

	for (__int32 i = 10; i < TDC8HP.number_of_doubles; ++i) {
		double double_dummy;
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
	}

	return byte_counter;
}












/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC8HPHeader_LMFV_1_to_7(__int32 byte_counter_external)
/////////////////////////////////////////////////////////////////
{
	this->TDC8HP.ui32oldRollOver = 0;
	this->TDC8HP.ui64RollOvers = 0;
	this->TDC8HP.ui32AbsoluteTimeStamp = 0;
	this->TDC8HP.ui64TDC8HP_AbsoluteTimeStamp = 0;

	__int32		byte_counter = 0;

	unsigned __int64 StartPosition1 = input_lmf->tell();

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	//	input_lmf->flush();
	unsigned __int64 StartPosition = input_lmf->tell();
	__int32 old_byte_counter = byte_counter;
L50:
	byte_counter = old_byte_counter;

	if (DAQVersion > 20080000) TDC8HP.UserHeaderVersion = 4;

	if (TDC8HP.UserHeaderVersion >= 1) {
		*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
		if (LMF_Version == 8) TDC8HP.UserHeaderVersion = 5;
		if (LMF_Version >= 9) TDC8HP.UserHeaderVersion = 6;
		if (LMF_Version >= 10) TDC8HP.UserHeaderVersion = 7;
		if (LMF_Version >= 11) TDC8HP.UserHeaderVersion = 8;
	}

	if (TDC8HP.UserHeaderVersion >= 5) {
		input_lmf->seek(StartPosition1);
		if (TDC8HP.UserHeaderVersion < 7) return ReadTDC8HPHeader_LMFV_8_to_9();
		return ReadTDC8HPHeader_LMFV_10();
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns
	if (tdcresolution < 0.0001 || tdcresolution > 100.) {
		if (TDC8HP.UserHeaderVersion != 0) return 0;
		TDC8HP.UserHeaderVersion = 1;

		input_lmf->seek(StartPosition);
		goto L50;
	}
	//tdcresolution = double(__int32(tdcresolution*1000000+0.01))/1000000.;
	if (TDC8HP.UserHeaderVersion >= 1) {
		*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);
	}


	unsigned __int64 TempPosition = input_lmf->tell();
	bool bRead32bit = false;

L100:

	if (DAQVersion < 20080000 || bRead32bit) {
		*input_lmf >> number_of_channels; byte_counter += sizeof(__int32);			// number of channels
	}
	else {
		unsigned __int64 temp;
		*input_lmf >> temp;
		if (temp > 4000000000) {
			input_lmf->seek(TempPosition);
			bRead32bit = true;
			goto L100;
		}
		number_of_channels = __int32(temp);
		byte_counter += sizeof(unsigned __int64);			// number of channels
	}

	if (number_of_channels < 1 || number_of_channels > 100) {
		if (TDC8HP.UserHeaderVersion != 0) return 0;
		//		in_ar->Close(); delete in_ar; in_ar = 0;
		input_lmf->seek(StartPosition);
		//		in_ar = new CArchive(input_lmf,CArchive::load);
		goto L50;
	}


	if (DAQVersion < 20080000 || bRead32bit) {
		*input_lmf >> max_number_of_hits; byte_counter += sizeof(__int32);			// number of hits
	}
	else {
		unsigned __int64 temp;
		*input_lmf >> temp;
		max_number_of_hits = __int32(temp);
		byte_counter += sizeof(unsigned __int64);			// number of hits
	}

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	if (max_number_of_hits < 1 || max_number_of_hits > 100) {
		if (TDC8HP.UserHeaderVersion != 0) return 0;
		//		in_ar->Close(); delete in_ar; in_ar = 0;
		input_lmf->seek(StartPosition);
		//		in_ar = new CArchive(input_lmf,CArchive::load);
		goto L50;
	}

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)
	*input_lmf >> TDC8HP.no_config_file_read;	byte_counter += sizeof(__int32);	// parameter 60-1
	if (DAQVersion < 20080000 || bRead32bit) {
		unsigned __int32 temp;
		*input_lmf >> temp; TDC8HP.RisingEnable_p61 = temp;		byte_counter += sizeof(__int32);	// parameter 61-1
		*input_lmf >> temp; TDC8HP.FallingEnable_p62 = temp;		byte_counter += sizeof(__int32);	// parameter 62-1
	}
	else {
		*input_lmf >> TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
		*input_lmf >> TDC8HP.FallingEnable_p62;		byte_counter += sizeof(__int64);	// parameter 62-1
	}
	*input_lmf >> TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*input_lmf >> TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1
	*input_lmf >> TDC8HP.OutputLevel_p65;		byte_counter += sizeof(__int32);	// parameter 65-1
	*input_lmf >> TDC8HP.GroupingEnable_p66;	byte_counter += sizeof(__int32);	// parameter 66-1
	*input_lmf >> TDC8HP.AllowOverlap_p67;		byte_counter += sizeof(__int32);	// parameter 67-1
	*input_lmf >> TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);		// parameter 68-1
	*input_lmf >> TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);		// parameter 69-1
	*input_lmf >> TDC8HP.GroupRangeEnd_p70;		byte_counter += sizeof(double);		// parameter 70-1
	*input_lmf >> TDC8HP.ExternalClock_p71;		byte_counter += sizeof(__int32);	// parameter 71-1
	*input_lmf >> TDC8HP.OutputRollOvers_p72;	byte_counter += sizeof(__int32);	// parameter 72-1
	*input_lmf >> TDC8HP.DelayTap0_p73;			byte_counter += sizeof(__int32);	// parameter 73-1
	*input_lmf >> TDC8HP.DelayTap1_p74;			byte_counter += sizeof(__int32);	// parameter 74-1
	*input_lmf >> TDC8HP.DelayTap2_p75;			byte_counter += sizeof(__int32);	// parameter 75-1
	*input_lmf >> TDC8HP.DelayTap3_p76;			byte_counter += sizeof(__int32);	// parameter 76-1
	*input_lmf >> TDC8HP.INL_p80;				byte_counter += sizeof(__int32);	// parameter 80-1
	*input_lmf >> TDC8HP.DNL_p81;				byte_counter += sizeof(__int32);	// parameter 81-1

	*input_lmf >> TDC8HP.csConfigFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csConfigFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csConfigFile_Length);
	__int8_temp[TDC8HP.csConfigFile_Length] = 0;
	TDC8HP.csConfigFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csConfigFile_Length;

	*input_lmf >> TDC8HP.csINLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csINLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csINLFile_Length);
	__int8_temp[TDC8HP.csINLFile_Length] = 0;
	TDC8HP.csINLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csINLFile_Length;

	*input_lmf >> TDC8HP.csDNLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csDNLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csDNLFile_Length);
	__int8_temp[TDC8HP.csDNLFile_Length] = 0;
	TDC8HP.csDNLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csDNLFile_Length;

	if (DAQVersion < 20080000) {
		if (byte_counter == __int32(User_header_size - 12 - 4)) {  // Cobold 2002 v11
			if (TDC8HP.UserHeaderVersion < 2) TDC8HP.UserHeaderVersion = 2;
			*input_lmf >> TDC8HP.SyncValidationChannel;  byte_counter += sizeof(__int32); 	// parameter 77-1
		}
		if (byte_counter == __int32(User_header_size - 12 - 4 - 4)) { // never used in official Cobold releases
			TDC8HP.UserHeaderVersion = 3;
			*input_lmf >> TDC8HP.SyncValidationChannel;  byte_counter += sizeof(__int32);
			*input_lmf >> TDC8HP.VHR_25ps;				 byte_counter += sizeof(bool);
		}
	}
	else {
		if (this->data_format_in_userheader == -1) TDC8HP.variable_event_length = 1;
		*input_lmf >> TDC8HP.SyncValidationChannel;  byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.VHR_25ps;  byte_counter += sizeof(bool);

		*input_lmf >> TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);

		*input_lmf >> TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
		*input_lmf >> TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
		*input_lmf >> TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

		unsigned __int64 TempPosition = input_lmf->tell();
		bool bNoTDCInfoRead = false;
		__int32 old_byte_counter2 = byte_counter;

	L200:
		byte_counter = old_byte_counter2;
		input_lmf->seek(TempPosition);

		if (!bNoTDCInfoRead) {
			// read TDCInfo
			*input_lmf >> TDC8HP.Number_of_TDCs;  byte_counter += sizeof(__int32);
			if (TDC8HP.Number_of_TDCs < 0 || TDC8HP.Number_of_TDCs>3) { bNoTDCInfoRead = true;	goto L200; }
			for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
				*input_lmf >> TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
				*input_lmf >> TDC8HP.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->version;				byte_counter += sizeof(__int32);
				*input_lmf >> TDC8HP.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
				input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);	byte_counter += sizeof(__int32) * 8 * 1024;
				input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
				*input_lmf >> TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
			}
		}

		bool bool_dummy;
		*input_lmf >> bool_dummy; byte_counter += sizeof(bool);
		*input_lmf >> bool_dummy; byte_counter += sizeof(bool);
		*input_lmf >> bool_dummy; byte_counter += sizeof(bool);
		*input_lmf >> bool_dummy; byte_counter += sizeof(bool);
		*input_lmf >> bool_dummy; byte_counter += sizeof(bool);

		*input_lmf >> TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
		if (TDC8HP.i32NumberOfDAQLoops == 0x12345678) TDC8HP.i32NumberOfDAQLoops = 1;
		*input_lmf >> TDC8HP.TDC8HP_DriverVersion;	byte_counter += sizeof(__int32);
		if (TDC8HP.TDC8HP_DriverVersion == 0x12345678) TDC8HP.TDC8HP_DriverVersion = 0;
		*input_lmf >> TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
		if (TDC8HP.iTriggerChannelMask == 0x12345678) TDC8HP.iTriggerChannelMask = 0;
		*input_lmf >> TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32);
		if (TDC8HP.iTime_zero_channel == 0x12345678) TDC8HP.iTime_zero_channel = -1;

		if (TDC8HP.i32NumberOfDAQLoops != 0x12345678) {
			if (TDC8HP.i32NumberOfDAQLoops < -2 || TDC8HP.i32NumberOfDAQLoops > 2e6) { bNoTDCInfoRead = true;	goto L200; }
		}

		if (TDC8HP.iTime_zero_channel != 0x12345678) {
			if (TDC8HP.iTime_zero_channel < -1 || TDC8HP.iTime_zero_channel  > 50) { bNoTDCInfoRead = true;	goto L200; }
		}

		__int32 int_dummy;
		*input_lmf >> int_dummy; byte_counter += sizeof(__int32);

		double double_dummy;
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
		*input_lmf >> double_dummy; byte_counter += sizeof(double);

		if (!bNoTDCInfoRead && (byte_counter_external + byte_counter == __int32(User_header_size + 4))) { bNoTDCInfoRead = true;	goto L200; }
	}

	if (bRead32bit && LMF_Version == 6) {
		TDC8HP.exotic_file_type = 1;
	}

	return byte_counter;
}











/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC8HPHeader_LMFV_8_to_9()
// reads LMF headers from Cobold 2008 R2 (release August 2009)
/////////////////////////////////////////////////////////////////
{
	this->TDC8HP.ui32oldRollOver = 0;
	this->TDC8HP.ui64RollOvers = 0;
	this->TDC8HP.ui32AbsoluteTimeStamp = 0;
	this->TDC8HP.ui64TDC8HP_AbsoluteTimeStamp = 0;

	__int32		byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	//	input_lmf->flush();
		//unsigned __int64 StartPosition = input_lmf->tell();
	__int32 old_byte_counter = byte_counter;

	byte_counter = old_byte_counter;

	if (DAQVersion > 20080000) TDC8HP.UserHeaderVersion = 4;

	if (TDC8HP.UserHeaderVersion >= 1) {
		*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
		if (LMF_Version == 8) TDC8HP.UserHeaderVersion = 5;
		if (LMF_Version >= 9) TDC8HP.UserHeaderVersion = 6;
	}

	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;    byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;     byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns
	*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;
	number_of_channels = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of channels

	*input_lmf >> temp_uint64;
	max_number_of_hits = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of hits

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	bool temp_bool;

	*input_lmf >> temp_bool; TDC8HP.no_config_file_read = temp_bool; byte_counter += sizeof(bool);	// parameter 60-1

	*input_lmf >> TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*input_lmf >> TDC8HP.FallingEnable_p62;		byte_counter += sizeof(__int64);	// parameter 62-1
	*input_lmf >> TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*input_lmf >> TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1

	*input_lmf >> temp_bool; TDC8HP.OutputLevel_p65 = temp_bool;	byte_counter += sizeof(bool);	// parameter 65-1
	*input_lmf >> temp_bool; TDC8HP.GroupingEnable_p66 = temp_bool;	byte_counter += sizeof(bool);	// parameter 66-1
	*input_lmf >> temp_bool; TDC8HP.AllowOverlap_p67 = temp_bool;	byte_counter += sizeof(bool);	// parameter 67-1

	*input_lmf >> TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);		// parameter 68-1
	*input_lmf >> TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);		// parameter 69-1
	*input_lmf >> TDC8HP.GroupRangeEnd_p70;		byte_counter += sizeof(double);		// parameter 70-1

	*input_lmf >> temp_bool; TDC8HP.ExternalClock_p71 = temp_bool;	byte_counter += sizeof(bool);	// parameter 71-1
	*input_lmf >> temp_bool; TDC8HP.OutputRollOvers_p72 = temp_bool;	byte_counter += sizeof(bool);	// parameter 72-1

	*input_lmf >> TDC8HP.DelayTap0_p73;			byte_counter += sizeof(__int32);	// parameter 73-1
	*input_lmf >> TDC8HP.DelayTap1_p74;			byte_counter += sizeof(__int32);	// parameter 74-1
	*input_lmf >> TDC8HP.DelayTap2_p75;			byte_counter += sizeof(__int32);	// parameter 75-1
	*input_lmf >> TDC8HP.DelayTap3_p76;			byte_counter += sizeof(__int32);	// parameter 76-1

	*input_lmf >> temp_bool; TDC8HP.INL_p80 = temp_bool;	byte_counter += sizeof(bool);	// parameter 80-1
	*input_lmf >> temp_bool; TDC8HP.DNL_p81 = temp_bool;	byte_counter += sizeof(bool);	// parameter 81-1

	*input_lmf >> TDC8HP.csConfigFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csConfigFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csConfigFile_Length);
	__int8_temp[TDC8HP.csConfigFile_Length] = 0;
	TDC8HP.csConfigFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csConfigFile_Length;

	*input_lmf >> TDC8HP.csINLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csINLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csINLFile_Length);
	__int8_temp[TDC8HP.csINLFile_Length] = 0;
	TDC8HP.csINLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csINLFile_Length;

	*input_lmf >> TDC8HP.csDNLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csDNLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csDNLFile_Length);
	__int8_temp[TDC8HP.csDNLFile_Length] = 0;
	TDC8HP.csDNLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csDNLFile_Length;

	if (this->data_format_in_userheader == -1) TDC8HP.variable_event_length = 1;
	*input_lmf >> TDC8HP.SyncValidationChannel;  byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.VHR_25ps;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);
	*input_lmf >> TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

	//// read TDCInfo
	*input_lmf >> TDC8HP.Number_of_TDCs;  byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*input_lmf >> TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelCount;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelStart;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*input_lmf >> TDC8HP.TDC_info[iCount]->serialNumber;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->version;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->fifoSize;				byte_counter += sizeof(__int32);
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*input_lmf >> TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC8HP.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 0; i < TDC8HP.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;	byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC8HP.number_of_int32s; byte_counter += sizeof(__int32);

	*input_lmf >> TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.TDC8HP_DriverVersion;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32); // 1 is first channel

	if (TDC8HP.UserHeaderVersion >= 6) {
		*input_lmf >> TDC8HP.BinsizeType;	byte_counter += sizeof(__int32); // 1 is first channel
		for (__int32 i = 5; i < TDC8HP.number_of_int32s; ++i) {
			__int32 int_dummy;
			*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
		}
	}
	else {
		for (__int32 i = 4; i < TDC8HP.number_of_int32s; ++i) {
			__int32 int_dummy;
			*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
		}
	}




	*input_lmf >> TDC8HP.number_of_doubles; byte_counter += sizeof(__int32);
	if (TDC8HP.UserHeaderVersion == 5) {
		for (__int32 i = 0; i < TDC8HP.number_of_doubles; ++i) {
			double double_dummy;
			*input_lmf >> double_dummy; byte_counter += sizeof(double);
		}
	}
	if (TDC8HP.UserHeaderVersion >= 6) {
		*input_lmf >> TDC8HP.OffsetTimeZeroChannel_s;  byte_counter += sizeof(double);
		for (__int32 i = 1; i < TDC8HP.number_of_doubles; ++i) {
			double double_dummy;
			*input_lmf >> double_dummy; byte_counter += sizeof(double);
		}
	}

	return byte_counter;
}





/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC8HQHeader()
/////////////////////////////////////////////////////////////////
{
	this->TDC8HQ.ui32oldRollOver = 0;
	this->TDC8HQ.ui64RollOvers = 0;
	this->TDC8HQ.ui32AbsoluteTimeStamp = 0;
	this->TDC8HQ.ui64TDC8HQ_AbsoluteTimeStamp = 0;

	__int32		byte_counter = 0;

	*input_lmf >> frequency;		byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;		byte_counter += sizeof(__int32);	// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;

	__int32 old_byte_counter = byte_counter;

	byte_counter = old_byte_counter;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
	TDC8HQ.UserHeaderVersion = 1;

	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;    byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;     byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns
	*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;
	number_of_channels = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of channels

	*input_lmf >> temp_uint64;
	max_number_of_hits = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of hits

	if (__int32(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (__int32(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	if (data_format_in_userheader < -10) data_format_in_userheader = -1;

	bool temp_bool;

	*input_lmf >> temp_bool;  byte_counter += sizeof(bool);	// parameter 60-1

	*input_lmf >> TDC8HQ.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*input_lmf >> TDC8HQ.FallingEnable_p62;		byte_counter += sizeof(__int64);	// parameter 62-1
	*input_lmf >> TDC8HQ.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*input_lmf >> TDC8HQ.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1

	*input_lmf >> temp_bool; TDC8HQ.OutputLevel_p65 = temp_bool;	byte_counter += sizeof(bool);	// parameter 65-1
	*input_lmf >> temp_bool; TDC8HQ.GroupingEnable_p66 = temp_bool;	byte_counter += sizeof(bool);	// parameter 66-1
	*input_lmf >> temp_bool; TDC8HQ.AllowOverlap_p67 = temp_bool;	byte_counter += sizeof(bool);	// parameter 67-1

	*input_lmf >> TDC8HQ.TriggerDeadTime_p68;	byte_counter += sizeof(double);		// parameter 68-1
	*input_lmf >> TDC8HQ.GroupRangeStart_p69;	byte_counter += sizeof(double);		// parameter 69-1
	*input_lmf >> TDC8HQ.GroupRangeEnd_p70;		byte_counter += sizeof(double);		// parameter 70-1

	*input_lmf >> temp_bool; TDC8HQ.ExternalClock_p71 = temp_bool;	byte_counter += sizeof(bool);	// parameter 71-1
	*input_lmf >> temp_bool; TDC8HQ.OutputRollOvers_p72 = temp_bool;	byte_counter += sizeof(bool);	// parameter 72-1

	*input_lmf >> TDC8HQ.DelayTap0_p73;			byte_counter += sizeof(__int32);	// parameter 73-1
	*input_lmf >> TDC8HQ.DelayTap1_p74;			byte_counter += sizeof(__int32);	// parameter 74-1
	*input_lmf >> TDC8HQ.DelayTap2_p75;			byte_counter += sizeof(__int32);	// parameter 75-1
	*input_lmf >> TDC8HQ.DelayTap3_p76;			byte_counter += sizeof(__int32);	// parameter 76-1

	*input_lmf >> temp_bool; TDC8HQ.INL_p80 = temp_bool;	byte_counter += sizeof(bool);	// parameter 80-1
	*input_lmf >> temp_bool; TDC8HQ.DNL_p81 = temp_bool;	byte_counter += sizeof(bool);	// parameter 81-1

	*input_lmf >> TDC8HQ.csConfigFile_Length;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.csINLFile_Length;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.csDNLFile_Length;	byte_counter += sizeof(__int32);

	TDC8HQ.variable_event_length = 1;
	*input_lmf >> TDC8HQ.SyncValidationChannel;  byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.VHR_25ps;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HQ.GroupTimeOut;  byte_counter += sizeof(double);
	*input_lmf >> TDC8HQ.SSEEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HQ.MMXEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HQ.DMAEnable;  byte_counter += sizeof(bool);

	//// read TDCInfo
	*input_lmf >> TDC8HQ.Number_of_TDCs;  byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HQ.Number_of_TDCs; ++iCount) {
		*input_lmf >> TDC8HQ.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->version;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HQ.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
		input_lmf->read((__int8*)TDC8HQ.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		input_lmf->read((__int8*)TDC8HQ.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*input_lmf >> TDC8HQ.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}


	*input_lmf >> TDC8HQ.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 0; i < TDC8HQ.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;	byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC8HQ.number_of_int32s; byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.TDC8HQ_DriverVersion;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.iTriggerChannelMask;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.iTime_zero_channel;	byte_counter += sizeof(__int32); // 1 means: first channel
	*input_lmf >> TDC8HQ.BinsizeType;	byte_counter += sizeof(__int32); // 1 means: first channel
	*input_lmf >> TDC8HQ.UseATC1;		byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.max_parameter_900_index;		byte_counter += sizeof(__int32);

	for (__int32 i = 7; i < TDC8HQ.number_of_int32s; ++i) {
		__int32 int_dummy;
		*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
	}

	*input_lmf >> TDC8HQ.number_of_doubles;			byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HQ.OffsetTimeZeroChannel_s;	byte_counter += sizeof(double);

	double double_dummy = 0.;

	*input_lmf >> TDC8HQ.veto_start;						byte_counter += sizeof(double);// veto start
	*input_lmf >> TDC8HQ.veto_end;							byte_counter += sizeof(double);// veto end
	*input_lmf >> double_dummy;								byte_counter += sizeof(double);// filter mask 1
	TDC8HQ.filter_mask_1 = (unsigned __int64)double_dummy;
	*input_lmf >> double_dummy;								byte_counter += sizeof(double);// filter mask 2
	TDC8HQ.filter_mask_2 = (unsigned __int64)double_dummy;
	*input_lmf >> double_dummy;								byte_counter += sizeof(double);// TDC_grp_config->i32AdvancedTriggerChannel for advanced trigger logic: dT = trigger_signal - TDC_grp_config->i32AdvancedTriggerChannel_signal   (0 = disabled)
	TDC8HQ.i32AdvancedTriggerChannel = __int32(double_dummy);
	*input_lmf >> TDC8HQ.i32AdvancedTriggerChannel_start;	byte_counter += sizeof(double);// window (ns) for advanced trigger logic: trigger only if dT is larger    AND...
	*input_lmf >> TDC8HQ.i32AdvancedTriggerChannel_stop;	byte_counter += sizeof(double);// window (ns) for advanced trigger logic: trigger only if dT is smaller
	*input_lmf >> TDC8HQ.Time_zero_channel_offset_s;		byte_counter += sizeof(double);// offset for signals in time zero channel (unit: seconds) (redundant to TDC_grp_config->zero_channel_offset above)

	*input_lmf >> double_dummy;  byte_counter += sizeof(double);
	__int32 nof_parameters = __int32(double_dummy + 0.1);

	for (__int32 i = 0; i < nof_parameters; ++i) {
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
		Parameter[i] = double_dummy;
	}

	if (User_header_size == byte_counter + 20)
		return byte_counter;

	*input_lmf >> double_dummy; byte_counter += sizeof(double);// veto exclusion mask
	TDC8HQ.veto_exclusion_mask = (unsigned __int64)double_dummy;

	// read more double that might be there:
	for (__int32 i = 1 + 8 + 1 + nof_parameters + 1; i < TDC8HQ.number_of_doubles; ++i) {
		double double_dummy;
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
	}

	return byte_counter;
}



/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTDC8HPHeader_LMFV_10()
// reads LMF headers from Cobold 2011 R1+R2
/////////////////////////////////////////////////////////////////
{
	this->TDC8HP.ui32oldRollOver = 0;
	this->TDC8HP.ui64RollOvers = 0;
	this->TDC8HP.ui32AbsoluteTimeStamp = 0;
	this->TDC8HP.ui64TDC8HP_AbsoluteTimeStamp = 0;

	__int32		byte_counter = 0;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;



	//	input_lmf->flush();
		//unsigned __int64 StartPosition = input_lmf->tell();
	__int32 old_byte_counter = byte_counter;

	byte_counter = old_byte_counter;

	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
	TDC8HP.UserHeaderVersion = 7;

	*input_lmf >> this->number_of_DAQ_source_strings;  byte_counter += sizeof(__int32);

	DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
	memset(DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) {
		__int32 string_len;
		*input_lmf >> string_len;    byte_counter += sizeof(__int32);
		DAQ_source_strings[i] = new std::string();
		DAQ_source_strings[i]->reserve(string_len);
		while (string_len > 0) {
			__int8 c;
			*input_lmf >> c;     byte_counter += sizeof(__int8);
			*DAQ_source_strings[i] += c;
			--string_len;
		}
	}

	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns
	*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);

	unsigned __int64 temp_uint64;
	*input_lmf >> temp_uint64;
	number_of_channels = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of channels

	*input_lmf >> temp_uint64;
	max_number_of_hits = __int32(temp_uint64);
	byte_counter += sizeof(unsigned __int64);			// number of hits

	if (__int32(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (__int32(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);	// data format (2=short integer)

	if (data_format_in_userheader < -10) data_format_in_userheader = -1;

	bool temp_bool;

	*input_lmf >> temp_bool; TDC8HP.no_config_file_read = temp_bool; byte_counter += sizeof(bool);	// parameter 60-1

	*input_lmf >> TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*input_lmf >> TDC8HP.FallingEnable_p62;		byte_counter += sizeof(__int64);	// parameter 62-1
	*input_lmf >> TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*input_lmf >> TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1

	*input_lmf >> temp_bool; TDC8HP.OutputLevel_p65 = temp_bool;	byte_counter += sizeof(bool);	// parameter 65-1
	*input_lmf >> temp_bool; TDC8HP.GroupingEnable_p66 = temp_bool;	byte_counter += sizeof(bool);	// parameter 66-1
	*input_lmf >> temp_bool; TDC8HP.AllowOverlap_p67 = temp_bool;	byte_counter += sizeof(bool);	// parameter 67-1

	*input_lmf >> TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);		// parameter 68-1
	*input_lmf >> TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);		// parameter 69-1
	*input_lmf >> TDC8HP.GroupRangeEnd_p70;		byte_counter += sizeof(double);		// parameter 70-1

	*input_lmf >> temp_bool; TDC8HP.ExternalClock_p71 = temp_bool;	byte_counter += sizeof(bool);	// parameter 71-1
	*input_lmf >> temp_bool; TDC8HP.OutputRollOvers_p72 = temp_bool;	byte_counter += sizeof(bool);	// parameter 72-1

	*input_lmf >> TDC8HP.DelayTap0_p73;			byte_counter += sizeof(__int32);	// parameter 73-1
	*input_lmf >> TDC8HP.DelayTap1_p74;			byte_counter += sizeof(__int32);	// parameter 74-1
	*input_lmf >> TDC8HP.DelayTap2_p75;			byte_counter += sizeof(__int32);	// parameter 75-1
	*input_lmf >> TDC8HP.DelayTap3_p76;			byte_counter += sizeof(__int32);	// parameter 76-1

	*input_lmf >> temp_bool; TDC8HP.INL_p80 = temp_bool;	byte_counter += sizeof(bool);	// parameter 80-1
	*input_lmf >> temp_bool; TDC8HP.DNL_p81 = temp_bool;	byte_counter += sizeof(bool);	// parameter 81-1

	*input_lmf >> TDC8HP.csConfigFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csConfigFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csConfigFile_Length);
	__int8_temp[TDC8HP.csConfigFile_Length] = 0;
	TDC8HP.csConfigFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csConfigFile_Length;

	*input_lmf >> TDC8HP.csINLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csINLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csINLFile_Length);
	__int8_temp[TDC8HP.csINLFile_Length] = 0;
	TDC8HP.csINLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csINLFile_Length;

	*input_lmf >> TDC8HP.csDNLFile_Length;
	byte_counter += sizeof(__int32);
	__int8_temp = new __int8[TDC8HP.csDNLFile_Length + 1];
	input_lmf->read(__int8_temp, TDC8HP.csDNLFile_Length);
	__int8_temp[TDC8HP.csDNLFile_Length] = 0;
	TDC8HP.csDNLFile = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += TDC8HP.csDNLFile_Length;

	if (this->data_format_in_userheader == -1) TDC8HP.variable_event_length = 1;
	*input_lmf >> TDC8HP.SyncValidationChannel;  byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.VHR_25ps;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);
	*input_lmf >> TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
	*input_lmf >> TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

	//// read TDCInfo
	*input_lmf >> TDC8HP.Number_of_TDCs;  byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*input_lmf >> TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelCount;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->channelStart;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*input_lmf >> TDC8HP.TDC_info[iCount]->serialNumber;			byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->version;				byte_counter += sizeof(__int32);
		*input_lmf >> TDC8HP.TDC_info[iCount]->fifoSize;				byte_counter += sizeof(__int32);
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		input_lmf->read((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*input_lmf >> TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC8HP.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 0; i < TDC8HP.number_of_bools; ++i) {
		bool bool_dummy;
		*input_lmf >> bool_dummy;	byte_counter += sizeof(bool);
	}

	*input_lmf >> TDC8HP.number_of_int32s; byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.TDC8HP_DriverVersion;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32); // 1 means: first channel
	*input_lmf >> TDC8HP.BinsizeType;	byte_counter += sizeof(__int32); // 1 means: first channel
	for (__int32 i = 5; i < TDC8HP.number_of_int32s; ++i) {
		__int32 int_dummy;
		*input_lmf >> int_dummy;	byte_counter += sizeof(__int32);
	}

	*input_lmf >> TDC8HP.number_of_doubles; byte_counter += sizeof(__int32);
	*input_lmf >> TDC8HP.OffsetTimeZeroChannel_s;  byte_counter += sizeof(double);
	for (__int32 i = 1; i < TDC8HP.number_of_doubles; ++i) {
		double double_dummy;
		*input_lmf >> double_dummy; byte_counter += sizeof(double);
	}

	return byte_counter;
}











/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadTCPIPHeader()
/////////////////////////////////////////////////////////////////
{
	__int32	byte_counter = 0;


	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;
	*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
	*input_lmf >> time_reference; byte_counter += sizeof(__int32);

	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);
	*input_lmf >> number_of_channels;			byte_counter += sizeof(__int32);
	*input_lmf >> max_number_of_hits;			byte_counter += sizeof(__int32);

	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }

	tdcresolution = 1.;

	return byte_counter;
}














/////////////////////////////////////////////////////////////////
__int32	LMF_IO::ReadHM1Header()
/////////////////////////////////////////////////////////////////
{
	__int32		byte_counter;
	byte_counter = 0;

	HM1.use_normal_method = false;

	*input_lmf >> frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*input_lmf >> IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*input_lmf >> timestamp_format;	byte_counter += sizeof(__int32);	// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	*input_lmf >> DAQ_info_Length;	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	__int8* __int8_temp = new __int8[DAQ_info_Length + 1];
	input_lmf->read(__int8_temp, DAQ_info_Length);	// DAQInfo always 8th value
	__int8_temp[DAQ_info_Length] = 0;
	DAQ_info = __int8_temp;
	delete[] __int8_temp; __int8_temp = 0;
	byte_counter += DAQ_info_Length;


	__int32 nominalHeaderLength;
	nominalHeaderLength = sizeof(__int32) * 21 + sizeof(double) * 2 + DAQ_info_Length;	// size of user defined header
	if (DAQ_ID == DAQ_ID_HM1_ABM) nominalHeaderLength += 24 * sizeof(__int32);

	if (DAQVersion >= 20080507) HM1.use_normal_method = true;

	if (nominalHeaderLength == __int32(User_header_size)) HM1.use_normal_method = true;

	if (DAQVersion >= 20020408 && HM1.use_normal_method) {
		*input_lmf >> LMF_Version; byte_counter += sizeof(__int32);
	}

	*input_lmf >> system_timeout; byte_counter += sizeof(__int32);		//   system time-out
	*input_lmf >> time_reference; byte_counter += sizeof(__int32);
	*input_lmf >> HM1.FAK_DLL_Value; byte_counter += sizeof(__int32);
	*input_lmf >> HM1.Resolution_Flag; byte_counter += sizeof(__int32);
	*input_lmf >> HM1.trigger_mode_for_start; byte_counter += sizeof(__int32);
	*input_lmf >> HM1.trigger_mode_for_stop; byte_counter += sizeof(__int32);
	*input_lmf >> tdcresolution; byte_counter += sizeof(double);		// tdc resolution in ns

	if (DAQVersion >= 20020408 && HM1.use_normal_method) {
		*input_lmf >> TDCDataType; byte_counter += sizeof(__int32);
	}

	*input_lmf >> HM1.Even_open_time; byte_counter += sizeof(__int32);
	*input_lmf >> HM1.Auto_Trigger; byte_counter += sizeof(__int32);

	if (DAQVersion >= 20020408) {
		__int64 i64_dummy;
		*input_lmf >> i64_dummy; number_of_channels = (unsigned __int32)i64_dummy; byte_counter += sizeof(__int64);			// number of channels
		*input_lmf >> i64_dummy; max_number_of_hits = (unsigned __int32)i64_dummy; byte_counter += sizeof(__int64);			// number of hits
	}
	else {
		*input_lmf >> number_of_channels; byte_counter += sizeof(__int32);			// number of channels
		*input_lmf >> max_number_of_hits; byte_counter += sizeof(__int32);			// number of hits
	}
	if (int(number_of_channels) > num_channels) { errorflag = 19;	return -100000; }
	if (int(max_number_of_hits) > num_ions) { errorflag = 20;	return -100000; }
	*input_lmf >> HM1.set_bits_for_GP1; byte_counter += sizeof(__int32);
	*input_lmf >> data_format_in_userheader;	byte_counter += sizeof(__int32);				// data format (2=short integer)
	*input_lmf >> module_2nd;	byte_counter += sizeof(__int32);		// indicator for 2nd module data

	if (DAQ_ID == DAQ_ID_2HM1) {
		*input_lmf >> DAQSubVersion;						byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_FAK_DLL_Value;				byte_counter += sizeof(__int32);  // parameter 10-1
		*input_lmf >> HM1.TWOHM1_Resolution_Flag;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_trigger_mode_for_start;	byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_trigger_mode_for_stop;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_res_adjust;				byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_tdcresolution;				byte_counter += sizeof(double);
		*input_lmf >> HM1.TWOHM1_test_overflow;				byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_number_of_channels;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_number_of_hits;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_set_bits_for_GP1;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_HM1_ID_1;					byte_counter += sizeof(__int32);
		*input_lmf >> HM1.TWOHM1_HM1_ID_2;					byte_counter += sizeof(__int32);
	}

	if (DAQ_ID == DAQ_ID_HM1_ABM) {
		max_number_of_hits = 1;
		*input_lmf >> HM1.ABM_m_xFrom;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_xTo;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_yFrom;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_yTo;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_xMin;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_xMax;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_yMin;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_yMax;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_xOffset;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_yOffset;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_m_zOffset;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_Mode;				byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_OsziDarkInvert;	byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_ErrorHisto;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_XShift;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_YShift;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_ZShift;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_ozShift;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_wdShift;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_ucLevelXY;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_ucLevelZ;			byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_uiABMXShift;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_uiABMYShift;		byte_counter += sizeof(__int32);
		*input_lmf >> HM1.ABM_uiABMZShift;		byte_counter += sizeof(__int32);
		if (DAQVersion > 20080507) {
			__int32 i32Dummy;
			*input_lmf >> i32Dummy;		byte_counter += sizeof(__int32);
		}
	}

	if (DAQ_ID == 1 && DAQVersion == 20080507 && LMF_Version == 7) {
		input_lmf->flush();
		input_lmf->seek(Headersize + User_header_size);
		input_lmf->flush();
	}

	return byte_counter;
}





























/////////////////////////////////////////////////////////////////
__int32 LMF_IO::WriteTCPIPHeader()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);
	*output_lmf << time_reference; byte_counter += sizeof(__int32);


	*output_lmf << data_format_in_userheader_output;					byte_counter += sizeof(__int32);
	*output_lmf << number_of_channels_output;			byte_counter += sizeof(__int32);
	*output_lmf << max_number_of_hits_output;			byte_counter += sizeof(__int32);

	return byte_counter;
}

















/////////////////////////////////////////////////////////////////
__int32	LMF_IO::Write2TDC8PCI2Header()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;
	//__int32 int_Dummy = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += __int32(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);

	*output_lmf << system_timeout_output; byte_counter += sizeof(__int32);		//   system time-out
	*output_lmf << time_reference_output; byte_counter += sizeof(__int32);
	*output_lmf << common_mode_output; byte_counter += sizeof(__int32);		//   0 common start    1 common stop
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	*output_lmf << TDCDataType; byte_counter += sizeof(__int32);
	*output_lmf << timerange; byte_counter += sizeof(__int32);	// time range of the tdc in microseconds

	*output_lmf << number_of_channels_output; byte_counter += sizeof(__int32);			// number of channels
	*output_lmf << max_number_of_hits_output; byte_counter += sizeof(__int32);			// number of hits
	*output_lmf << number_of_channels2_output; byte_counter += sizeof(__int32);	// number of channels2
	*output_lmf << max_number_of_hits2_output; byte_counter += sizeof(__int32);	// number of hits2
	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	if (TDC8PCI2.use_normal_method_2nd_card) {
		if (DAQVersion_output >= 20020408) {
			*output_lmf << TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
			*output_lmf << TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
			*output_lmf << TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
			*output_lmf << TDC8PCI2.TriggerFalling_1st_card;	byte_counter += sizeof(__int32); // trigger falling edge 1st card
			*output_lmf << TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card
			*output_lmf << TDC8PCI2.EmptyCounter_1st_card;		byte_counter += sizeof(__int32); // EmptyCounter 1st card
			*output_lmf << TDC8PCI2.EmptyCounter_since_last_Event_1st_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 1st card
		}
		*output_lmf << TDC8PCI2.sync_test_on_off;			byte_counter += sizeof(__int32); // sync test on/off
		*output_lmf << TDC8PCI2.io_address_2nd_card;		byte_counter += sizeof(__int32); // io address 2nd card
		*output_lmf << TDC8PCI2.GateDelay_2nd_card;			byte_counter += sizeof(__int32); // gate delay 2nd card
		*output_lmf << TDC8PCI2.OpenTime_2nd_card;			byte_counter += sizeof(__int32); // open time 2nd card
		*output_lmf << TDC8PCI2.WriteEmptyEvents_2nd_card;	byte_counter += sizeof(__int32); // write empty events 2nd card
		*output_lmf << TDC8PCI2.TriggerFallingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger falling edge 2nd card
		*output_lmf << TDC8PCI2.TriggerRisingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger rising edge 2nd card
		*output_lmf << TDC8PCI2.EmptyCounter_2nd_card;		byte_counter += sizeof(__int32); // EmptyCounter 2nd card
		*output_lmf << TDC8PCI2.EmptyCounter_since_last_Event_2nd_card;	byte_counter += sizeof(__int32); // Empty Counter since last event 2nd card
	}
	else {
		*output_lmf << module_2nd;							byte_counter += sizeof(__int32); // indicator for 2nd module data
		*output_lmf << TDC8PCI2.GateDelay_1st_card;			byte_counter += sizeof(__int32); // gate delay 1st card
		*output_lmf << TDC8PCI2.OpenTime_1st_card;			byte_counter += sizeof(__int32); // open time 1st card
		*output_lmf << TDC8PCI2.WriteEmptyEvents_1st_card;	byte_counter += sizeof(__int32); // write empty events 1st card
		*output_lmf << TDC8PCI2.TriggerFalling_1st_card;	byte_counter += sizeof(__int32); // trigger falling edge 1st card
		*output_lmf << TDC8PCI2.TriggerRising_1st_card;		byte_counter += sizeof(__int32); // trigger rising edge 1st card

		*output_lmf << TDC8PCI2.GateDelay_2nd_card;			byte_counter += sizeof(__int32); // gate delay 2nd card
		*output_lmf << TDC8PCI2.OpenTime_2nd_card;			byte_counter += sizeof(__int32); // open time 2nd card
		*output_lmf << TDC8PCI2.WriteEmptyEvents_2nd_card;	byte_counter += sizeof(__int32); // write empty events 2nd card
		*output_lmf << TDC8PCI2.TriggerFallingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger falling edge 2nd card
		*output_lmf << TDC8PCI2.TriggerRisingEdge_2nd_card;	byte_counter += sizeof(__int32); // trigger rising edge 2nd card
	}
	return byte_counter;
}






/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteTDC8HPHeader_LMFV_1_to_7()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;
	double	double_Dummy = 0.;
	__int32		int_Dummy = 0;
	//unsigned __int32 unsigned_int_Dummy = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	if ((DAQVersion_output >= 20020408 && TDC8HP.UserHeaderVersion >= 1) || TDC8HP.UserHeaderVersion >= 4) {
		*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);
	}

	*output_lmf << time_reference; byte_counter += sizeof(__int32);
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	if ((DAQVersion_output >= 20020408 && TDC8HP.UserHeaderVersion >= 1) || TDC8HP.UserHeaderVersion >= 4) { *output_lmf << TDCDataType; byte_counter += sizeof(__int32); }

	if (DAQVersion_output < 20080000) {
		*output_lmf << number_of_channels_output; byte_counter += sizeof(__int32);			// number of channels
		*output_lmf << max_number_of_hits_output; byte_counter += sizeof(__int32);			// number of hits
	}
	if (DAQVersion_output >= 20080000) {
		unsigned __int64 temp;
		temp = number_of_channels_output;	*output_lmf << temp; byte_counter += sizeof(unsigned __int64);			// number of channels
		temp = max_number_of_hits_output;	*output_lmf << temp; byte_counter += sizeof(unsigned __int64);			// number of hits
	}
	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	*output_lmf << TDC8HP.no_config_file_read;	byte_counter += sizeof(__int32);	// parameter 60-1
	if (DAQVersion_output < 20080000) {
		unsigned __int32 temp;
		temp = __int32(TDC8HP.RisingEnable_p61);  *output_lmf << temp;	byte_counter += sizeof(__int32);	// parameter 61-1
		temp = __int32(TDC8HP.FallingEnable_p62); *output_lmf << temp;	byte_counter += sizeof(__int32);	// parameter 62-1
	}
	if (DAQVersion_output >= 20080000) {
		*output_lmf << TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
		*output_lmf << TDC8HP.FallingEnable_p62;	byte_counter += sizeof(__int64);	// parameter 62-1
	}
	*output_lmf << TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*output_lmf << TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1
	*output_lmf << TDC8HP.OutputLevel_p65;		byte_counter += sizeof(__int32);	// parameter 65-1
	*output_lmf << TDC8HP.GroupingEnable_p66_output;	byte_counter += sizeof(__int32);	// parameter 66-1
	*output_lmf << TDC8HP.AllowOverlap_p67;		byte_counter += sizeof(__int32);	// parameter 67-1
	*output_lmf << TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);	// parameter 68-1
	*output_lmf << TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);	// parameter 69-1
	*output_lmf << TDC8HP.GroupRangeEnd_p70;	byte_counter += sizeof(double);	// parameter 70-1
	*output_lmf << TDC8HP.ExternalClock_p71;	byte_counter += sizeof(__int32);	// parameter 71-1
	*output_lmf << TDC8HP.OutputRollOvers_p72;	byte_counter += sizeof(__int32);	// parameter 72-1
	*output_lmf << TDC8HP.DelayTap0_p73;		byte_counter += sizeof(__int32);	// parameter 73-1
	*output_lmf << TDC8HP.DelayTap1_p74;		byte_counter += sizeof(__int32);	// parameter 74-1
	*output_lmf << TDC8HP.DelayTap2_p75;		byte_counter += sizeof(__int32);	// parameter 75-1
	*output_lmf << TDC8HP.DelayTap3_p76;		byte_counter += sizeof(__int32);	// parameter 76-1
	*output_lmf << TDC8HP.INL_p80;				byte_counter += sizeof(__int32);	// parameter 80-1
	*output_lmf << TDC8HP.DNL_p81;				byte_counter += sizeof(__int32);	// parameter 81-1

	dummy = __int32(TDC8HP.csConfigFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csConfigFile.c_str(), __int32(TDC8HP.csConfigFile.length()));
	byte_counter += __int32(TDC8HP.csConfigFile.length());

	dummy = __int32(TDC8HP.csINLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csINLFile.c_str(), __int32(TDC8HP.csINLFile.length()));
	byte_counter += __int32(TDC8HP.csINLFile.length());

	dummy = __int32(TDC8HP.csDNLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csDNLFile.c_str(), __int32(TDC8HP.csDNLFile.length()));
	byte_counter += __int32(TDC8HP.csDNLFile.length());

	if (TDC8HP.UserHeaderVersion >= 2) {
		*output_lmf << TDC8HP.SyncValidationChannel; byte_counter += sizeof(__int32);
	}
	if (TDC8HP.UserHeaderVersion >= 3) {
		*output_lmf << TDC8HP.VHR_25ps; byte_counter += sizeof(bool);
	}

	if (TDC8HP.UserHeaderVersion >= 4) {

		*output_lmf << TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);

		*output_lmf << TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
		*output_lmf << TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
		*output_lmf << TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

		//// write TDCInfo
		*output_lmf << TDC8HP.Number_of_TDCs;	byte_counter += sizeof(__int32);
		for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
			*output_lmf << TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
			*output_lmf << TDC8HP.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->version;			byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
			output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
			output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
			*output_lmf << TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
		}

		bool bool_dummy = false;
		*output_lmf << bool_dummy; byte_counter += sizeof(bool);
		*output_lmf << bool_dummy; byte_counter += sizeof(bool);
		*output_lmf << bool_dummy; byte_counter += sizeof(bool);
		*output_lmf << bool_dummy; byte_counter += sizeof(bool);
		*output_lmf << bool_dummy; byte_counter += sizeof(bool);

		*output_lmf << TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC8HP_DriverVersion; byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32);
		*output_lmf << int_Dummy;				byte_counter += sizeof(__int32);

		*output_lmf << double_Dummy; byte_counter += sizeof(double);
		*output_lmf << double_Dummy; byte_counter += sizeof(double);
		*output_lmf << double_Dummy; byte_counter += sizeof(double);
		*output_lmf << double_Dummy; byte_counter += sizeof(double);
		*output_lmf << double_Dummy; byte_counter += sizeof(double);
	}

	return byte_counter;
}












/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteTDC8HPHeader_LMFV_8_to_9()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter = 0;

	bool			 bool_dummy = false;
	//double			 double_Dummy	= 0.;
	//__int32			 int_Dummy		= 0;
	unsigned __int32 unsigned_int_Dummy = 0;
	__int64			 int64_dummy = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);

	if ((number_of_DAQ_source_strings_output < 0) || (!DAQ_source_strings_output)) number_of_DAQ_source_strings_output = 0;
	*output_lmf << number_of_DAQ_source_strings_output;  byte_counter += sizeof(__int32);

	for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
		unsigned_int_Dummy = (unsigned __int32)(DAQ_source_strings_output[i]->length());
		*output_lmf << unsigned_int_Dummy;   byte_counter += sizeof(__int32);
		output_lmf->write(DAQ_source_strings_output[i]->c_str(), __int32(DAQ_source_strings_output[i]->length()));
		byte_counter += (unsigned __int32)(DAQ_source_strings_output[i]->length());
	}

	*output_lmf << time_reference; byte_counter += sizeof(__int32);
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	*output_lmf << TDCDataType; byte_counter += sizeof(__int32);

	int64_dummy = number_of_channels_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of channels
	int64_dummy = max_number_of_hits_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of hits

	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	bool_dummy = TDC8HP.no_config_file_read ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 60-1
	*output_lmf << TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*output_lmf << TDC8HP.FallingEnable_p62;	byte_counter += sizeof(__int64);	// parameter 62-1

	*output_lmf << TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*output_lmf << TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1
	bool_dummy = TDC8HP.OutputLevel_p65 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 65-1
	bool_dummy = TDC8HP.GroupingEnable_p66_output ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 66-1
	bool_dummy = TDC8HP.AllowOverlap_p67 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 67-1
	*output_lmf << TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);	// parameter 68-1
	*output_lmf << TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);	// parameter 69-1
	*output_lmf << TDC8HP.GroupRangeEnd_p70;	byte_counter += sizeof(double);	// parameter 70-1
	bool_dummy = TDC8HP.ExternalClock_p71 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 71-1
	bool_dummy = TDC8HP.OutputRollOvers_p72 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 72-1
	*output_lmf << TDC8HP.DelayTap0_p73;		byte_counter += sizeof(__int32);	// parameter 73-1
	*output_lmf << TDC8HP.DelayTap1_p74;		byte_counter += sizeof(__int32);	// parameter 74-1
	*output_lmf << TDC8HP.DelayTap2_p75;		byte_counter += sizeof(__int32);	// parameter 75-1
	*output_lmf << TDC8HP.DelayTap3_p76;		byte_counter += sizeof(__int32);	// parameter 76-1
	bool_dummy = TDC8HP.INL_p80 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 80-1
	bool_dummy = TDC8HP.DNL_p81 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 81-1

	dummy = __int32(TDC8HP.csConfigFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csConfigFile.c_str(), __int32(TDC8HP.csConfigFile.length()));
	byte_counter += __int32(TDC8HP.csConfigFile.length());

	dummy = __int32(TDC8HP.csINLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csINLFile.c_str(), __int32(TDC8HP.csINLFile.length()));
	byte_counter += __int32(TDC8HP.csINLFile.length());

	dummy = __int32(TDC8HP.csDNLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csDNLFile.c_str(), __int32(TDC8HP.csDNLFile.length()));
	byte_counter += __int32(TDC8HP.csDNLFile.length());

	*output_lmf << TDC8HP.SyncValidationChannel; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.VHR_25ps; byte_counter += sizeof(bool);

	*output_lmf << TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);

	*output_lmf << TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
	*output_lmf << TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
	*output_lmf << TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

	//// write TDCInfo
	*output_lmf << TDC8HP.Number_of_TDCs;	byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*output_lmf << TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*output_lmf << TDC8HP.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->version;			byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
		output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*output_lmf << TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}


	*output_lmf << TDC8HP.number_of_bools; byte_counter += sizeof(__int32);
	for (__int32 i = 4; i < TDC8HP.number_of_bools; ++i) {
		bool bdummy = false;
		*output_lmf << bdummy; byte_counter += sizeof(bool);
	}

	if (TDC8HP.number_of_int32s < 4) TDC8HP.number_of_int32s = 4;
	if (TDC8HP.UserHeaderVersion >= 6) TDC8HP.number_of_int32s = 5;
	*output_lmf << TDC8HP.number_of_int32s; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.TDC8HP_DriverVersion; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32);

	if (TDC8HP.UserHeaderVersion == 5) {
		for (__int32 i = 4; i < TDC8HP.number_of_int32s; ++i) {
			__int32 idummy = 0;
			*output_lmf << idummy; byte_counter += sizeof(__int32);
		}
	}
	else {
		*output_lmf << TDC8HP.BinsizeType;	byte_counter += sizeof(__int32);
		for (__int32 i = 5; i < TDC8HP.number_of_int32s; ++i) {
			__int32 idummy = 0;
			*output_lmf << idummy; byte_counter += sizeof(__int32);
		}
	}

	if (TDC8HP.UserHeaderVersion == 5) {
		*output_lmf << TDC8HP.number_of_doubles; byte_counter += sizeof(__int32);
		for (__int32 i = 0; i < TDC8HP.number_of_doubles; ++i) {
			double ddummy = 0.;
			*output_lmf << ddummy; byte_counter += sizeof(double);
		}
	}
	if (TDC8HP.UserHeaderVersion >= 6) {
		if (TDC8HP.number_of_doubles == 0) {
			*output_lmf << __int32(1); byte_counter += sizeof(__int32);
			*output_lmf << double(0.); byte_counter += sizeof(double);
		}
		else {
			*output_lmf << TDC8HP.number_of_doubles; byte_counter += sizeof(__int32);
			*output_lmf << TDC8HP.OffsetTimeZeroChannel_s; byte_counter += sizeof(double);
			for (__int32 i = 1; i < TDC8HP.number_of_doubles; ++i) {
				double ddummy = 0.;
				*output_lmf << ddummy; byte_counter += sizeof(double);
			}
		}
	}

	return byte_counter;
}







/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteTDC8HPHeader_LMFV_10_to_12()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter = 0;

	bool			 bool_dummy = false;
	//double			 double_Dummy	= 0.;
	//__int32			 int_Dummy		= 0;
	unsigned __int32 unsigned_int_Dummy = 0;
	__int64			 int64_dummy = 0;

	number_of_bytes_in_PostEventData = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);

	if ((number_of_DAQ_source_strings_output < 0) || (!DAQ_source_strings_output)) number_of_DAQ_source_strings_output = 0;
	*output_lmf << number_of_DAQ_source_strings_output;  byte_counter += sizeof(__int32);

	for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
		unsigned_int_Dummy = (unsigned __int32)(DAQ_source_strings_output[i]->length());
		*output_lmf << unsigned_int_Dummy;   byte_counter += sizeof(__int32);
		output_lmf->write(DAQ_source_strings_output[i]->c_str(), __int32(DAQ_source_strings_output[i]->length()));
		byte_counter += (unsigned __int32)(DAQ_source_strings_output[i]->length());
	}

	*output_lmf << time_reference; byte_counter += sizeof(__int32);
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	*output_lmf << TDCDataType; byte_counter += sizeof(__int32);

	int64_dummy = number_of_channels_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of channels
	int64_dummy = max_number_of_hits_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of hits

	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	bool_dummy = TDC8HP.no_config_file_read ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 60-1
	*output_lmf << TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*output_lmf << TDC8HP.FallingEnable_p62;	byte_counter += sizeof(__int64);	// parameter 62-1

	*output_lmf << TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*output_lmf << TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1
	bool_dummy = TDC8HP.OutputLevel_p65 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 65-1
	bool_dummy = TDC8HP.GroupingEnable_p66_output ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 66-1
	bool_dummy = TDC8HP.AllowOverlap_p67 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 67-1
	*output_lmf << TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);	// parameter 68-1
	*output_lmf << TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);	// parameter 69-1
	*output_lmf << TDC8HP.GroupRangeEnd_p70;	byte_counter += sizeof(double);	// parameter 70-1
	bool_dummy = TDC8HP.ExternalClock_p71 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 71-1
	bool_dummy = TDC8HP.OutputRollOvers_p72 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 72-1
	*output_lmf << TDC8HP.DelayTap0_p73;		byte_counter += sizeof(__int32);	// parameter 73-1
	*output_lmf << TDC8HP.DelayTap1_p74;		byte_counter += sizeof(__int32);	// parameter 74-1
	*output_lmf << TDC8HP.DelayTap2_p75;		byte_counter += sizeof(__int32);	// parameter 75-1
	*output_lmf << TDC8HP.DelayTap3_p76;		byte_counter += sizeof(__int32);	// parameter 76-1
	bool_dummy = TDC8HP.INL_p80 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 80-1
	bool_dummy = TDC8HP.DNL_p81 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 81-1

	dummy = __int32(TDC8HP.csConfigFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csConfigFile.c_str(), __int32(TDC8HP.csConfigFile.length()));
	byte_counter += __int32(TDC8HP.csConfigFile.length());

	dummy = __int32(TDC8HP.csINLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csINLFile.c_str(), __int32(TDC8HP.csINLFile.length()));
	byte_counter += __int32(TDC8HP.csINLFile.length());

	dummy = __int32(TDC8HP.csDNLFile.length());
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	output_lmf->write(TDC8HP.csDNLFile.c_str(), __int32(TDC8HP.csDNLFile.length()));
	byte_counter += __int32(TDC8HP.csDNLFile.length());

	*output_lmf << TDC8HP.SyncValidationChannel; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.VHR_25ps; byte_counter += sizeof(bool);

	*output_lmf << TDC8HP.GroupTimeOut;  byte_counter += sizeof(double);

	*output_lmf << TDC8HP.SSEEnable;  byte_counter += sizeof(bool);
	*output_lmf << TDC8HP.MMXEnable;  byte_counter += sizeof(bool);
	*output_lmf << TDC8HP.DMAEnable;  byte_counter += sizeof(bool);

	//// write TDCInfo
	*output_lmf << TDC8HP.Number_of_TDCs;	byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*output_lmf << TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->channelCount;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelCount;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->highResChannelStart;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelCount;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->lowResChannelStart;	byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->resolution;			byte_counter += sizeof(double);
		*output_lmf << TDC8HP.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->version;			byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->fifoSize;			byte_counter += sizeof(__int32);
		output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->INLCorrection, sizeof(__int32) * 8 * 1024);		byte_counter += sizeof(__int32) * 8 * 1024;
		output_lmf->write((__int8*)TDC8HP.TDC_info[iCount]->DNLData, sizeof(unsigned __int16) * 8 * 1024);	byte_counter += sizeof(unsigned __int16) * 8 * 1024;
		*output_lmf << TDC8HP.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}


	TDC8HP.number_of_bools = 0;
	*output_lmf << TDC8HP.number_of_bools; byte_counter += sizeof(__int32);

	TDC8HP.number_of_int32s = 5;
	*output_lmf << TDC8HP.number_of_int32s; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.i32NumberOfDAQLoops;	byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.TDC8HP_DriverVersion; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.iTriggerChannelMask;	byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.iTime_zero_channel;	byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.BinsizeType;	byte_counter += sizeof(__int32);

	TDC8HP.number_of_doubles = 1;
	*output_lmf << TDC8HP.number_of_doubles; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HP.OffsetTimeZeroChannel_s; byte_counter += sizeof(double);
	for (__int32 i = 1; i < TDC8HP.number_of_doubles; ++i) {
		double ddummy = 0.;
		*output_lmf << ddummy; byte_counter += sizeof(double);
	}

	return byte_counter;
}




/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteTDC8HQHeader_v1()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter = 0;

	bool			 bool_dummy = false;
	//double			 double_Dummy	= 0.;
	//__int32			 int_Dummy		= 0;
	unsigned __int32 unsigned_int_Dummy = 0;
	__int64			 int64_dummy = 0;

	number_of_bytes_in_PostEventData = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value

	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += (unsigned __int32)(DAQ_info.length());

	*output_lmf << LMF_Version_output; byte_counter += sizeof(__int32);

	if ((number_of_DAQ_source_strings_output < 0) || (!DAQ_source_strings_output)) number_of_DAQ_source_strings_output = 0;
	*output_lmf << number_of_DAQ_source_strings_output;  byte_counter += sizeof(__int32);

	for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) {
		unsigned_int_Dummy = (unsigned __int32)(DAQ_source_strings_output[i]->length());
		*output_lmf << unsigned_int_Dummy;   byte_counter += sizeof(__int32);
		output_lmf->write(DAQ_source_strings_output[i]->c_str(), __int32(DAQ_source_strings_output[i]->length()));
		byte_counter += (unsigned __int32)(DAQ_source_strings_output[i]->length());
	}

	*output_lmf << time_reference; byte_counter += sizeof(__int32);
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	*output_lmf << TDCDataType; byte_counter += sizeof(__int32);

	int64_dummy = number_of_channels_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of channels
	int64_dummy = max_number_of_hits_output;
	*output_lmf << int64_dummy; byte_counter += sizeof(__int64);			// number of hits

	data_format_in_userheader_output = -1;
	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format

	bool_dummy = false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 60-1
	*output_lmf << TDC8HP.RisingEnable_p61;		byte_counter += sizeof(__int64);	// parameter 61-1
	*output_lmf << TDC8HP.FallingEnable_p62;	byte_counter += sizeof(__int64);	// parameter 62-1

	*output_lmf << TDC8HP.TriggerEdge_p63;		byte_counter += sizeof(__int32);	// parameter 63-1
	*output_lmf << TDC8HP.TriggerChannel_p64;	byte_counter += sizeof(__int32);	// parameter 64-1
	bool_dummy = TDC8HP.OutputLevel_p65 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 65-1
	bool_dummy = TDC8HP.GroupingEnable_p66_output ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 66-1
	bool_dummy = TDC8HP.AllowOverlap_p67 ? true : false;
	*output_lmf << bool_dummy;		byte_counter += sizeof(bool);	// parameter 67-1
	*output_lmf << TDC8HP.TriggerDeadTime_p68;	byte_counter += sizeof(double);	// parameter 68-1
	*output_lmf << TDC8HP.GroupRangeStart_p69;	byte_counter += sizeof(double);	// parameter 69-1
	*output_lmf << TDC8HP.GroupRangeEnd_p70;	byte_counter += sizeof(double);	// parameter 70-1
	bool_dummy = TDC8HP.ExternalClock_p71 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 71-1
	bool_dummy = TDC8HP.OutputRollOvers_p72 ? true : false;
	*output_lmf << bool_dummy;	byte_counter += sizeof(bool);	// parameter 72-1
	*output_lmf << TDC8HP.DelayTap0_p73;		byte_counter += sizeof(__int32);	// parameter 73-1
	*output_lmf << TDC8HP.DelayTap1_p74;		byte_counter += sizeof(__int32);	// parameter 74-1
	*output_lmf << TDC8HP.DelayTap2_p75;		byte_counter += sizeof(__int32);	// parameter 75-1
	*output_lmf << TDC8HP.DelayTap3_p76;		byte_counter += sizeof(__int32);	// parameter 76-1
	bool_dummy = TDC8HP.INL_p80 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 80-1
	bool_dummy = TDC8HP.DNL_p81 ? true : false;
	*output_lmf << bool_dummy;				byte_counter += sizeof(bool);	// parameter 81-1

	dummy = 0;
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	*output_lmf << dummy;	byte_counter += sizeof(__int32);
	*output_lmf << dummy;	byte_counter += sizeof(__int32);


	*output_lmf << dummy; byte_counter += sizeof(__int32);
	*output_lmf << true; byte_counter += sizeof(bool);

	*output_lmf << double(0.);  byte_counter += sizeof(double);

	*output_lmf << true;  byte_counter += sizeof(bool);
	*output_lmf << true;  byte_counter += sizeof(bool);
	*output_lmf << true;  byte_counter += sizeof(bool);

	//// write TDCInfo
	*output_lmf << TDC8HQ.Number_of_TDCs;	byte_counter += sizeof(__int32);
	for (__int32 iCount = 0; iCount < TDC8HP.Number_of_TDCs; ++iCount) {
		*output_lmf << TDC8HP.TDC_info[iCount]->index;				byte_counter += sizeof(__int32);
		*output_lmf << 10;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->channelStart;		byte_counter += sizeof(__int32);
		*output_lmf << 10;	byte_counter += sizeof(__int32);
		*output_lmf << 0;	byte_counter += sizeof(__int32);
		*output_lmf << 0;	byte_counter += sizeof(__int32);
		*output_lmf << 0;	byte_counter += sizeof(__int32);
		*output_lmf << tdcresolution_output;			byte_counter += sizeof(double);
		*output_lmf << TDC8HQ.TDC_info[iCount]->serialNumber;		byte_counter += sizeof(__int32);
		*output_lmf << TDC8HP.TDC_info[iCount]->version;			byte_counter += sizeof(__int32);
		*output_lmf << 0;			byte_counter += sizeof(__int32);
		for (__int32 i = 0; i < 8 * 1024; i++) *output_lmf << (__int32)0;  // was *output_lmf->Write(tdcBoard.INLCorrection,sizeof(__int32)*8*1024);
		for (__int32 i = 0; i < 8 * 1024; i++) *output_lmf << (__int16)0;  // was *output_lmf->Write(tdcBoard.DNLData,sizeof(unsigned __int16)*8*1024);
		*output_lmf << TDC8HQ.TDC_info[iCount]->flashValid;			byte_counter += sizeof(bool);
	}


	TDC8HQ.number_of_bools = 0;
	*output_lmf << TDC8HQ.number_of_bools; byte_counter += sizeof(__int32);

	TDC8HQ.number_of_int32s = 7;
	*output_lmf << TDC8HQ.number_of_int32s; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HQ.i32NumberOfDAQLoops;
	*output_lmf << (unsigned __int32)TDC8HQ.TDC8HQ_DriverVersion;

	*output_lmf << TDC8HQ.iTriggerChannelMask;
	*output_lmf << TDC8HQ.iTime_zero_channel;										// + 1, CCF Counting start from 1 not 0
	*output_lmf << __int32(0); // was i32BinsizeType

	*output_lmf << TDC8HQ.UseATC1; // use ATC1
	*output_lmf << TDC8HQ.max_parameter_900_index;

	TDC8HQ.number_of_doubles = 11;
	*output_lmf << TDC8HQ.number_of_doubles; byte_counter += sizeof(__int32);
	*output_lmf << TDC8HQ.OffsetTimeZeroChannel_s;
	*output_lmf << TDC8HQ.veto_start; // veto start
	*output_lmf << TDC8HQ.veto_end; // veto end
	*output_lmf << double(TDC8HQ.filter_mask_1); // filter mask 1
	*output_lmf << double(TDC8HQ.filter_mask_2); // filter mask 2
	*output_lmf << double(TDC8HQ.i32AdvancedTriggerChannel); // TDC_grp_config->i32AdvancedTriggerChannel for advanced trigger logic: dT = trigger_signal - TDC_grp_config->i32AdvancedTriggerChannel_signal   (0 = disabled)
	*output_lmf << double(TDC8HQ.i32AdvancedTriggerChannel_start); // window (ns) for advanced trigger logic: trigger only if dT is larger    AND...
	*output_lmf << double(TDC8HQ.i32AdvancedTriggerChannel_stop); // window (ns) for advanced trigger logic: trigger only if dT is smaller
	*output_lmf << double(TDC8HQ.Time_zero_channel_offset_s);	 // offset for signals in time zero channel (unit: seconds) (redundant to TDC_grp_config->zero_channel_offset above)

	*output_lmf << double(0.);
	*output_lmf << double(TDC8HQ.veto_exclusion_mask); // veto exclusion mask

	return byte_counter;
}





/////////////////////////////////////////////////////////////////
__int32 LMF_IO::WriteTDC4HMHeader()
/////////////////////////////////////////////////////////////////
{
	printf("Error: Writing TDC4HM-header is not yet implemented.\n");
	return 0;
}





/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteHM1Header()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;
	//__int32 int_Dummy = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = (unsigned __int32)(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += __int32(DAQ_info.length());

	if (DAQVersion_output >= 20020408 && HM1.use_normal_method) { *output_lmf << LMF_Version_output; byte_counter += sizeof(__int32); }

	*output_lmf << system_timeout_output; byte_counter += sizeof(__int32);		//   system time-out
	*output_lmf << time_reference_output; byte_counter += sizeof(__int32);
	if (DAQ_ID_output == DAQ_ID_HM1 || DAQ_ID_output == DAQ_ID_HM1_ABM) {
		*output_lmf << HM1.FAK_DLL_Value; byte_counter += sizeof(__int32);
		*output_lmf << HM1.Resolution_Flag; byte_counter += sizeof(__int32);
		*output_lmf << HM1.trigger_mode_for_start; byte_counter += sizeof(__int32);
		*output_lmf << HM1.trigger_mode_for_stop; byte_counter += sizeof(__int32);
	}
	*output_lmf << tdcresolution_output; byte_counter += sizeof(double);		// tdc resolution in ns

	TDCDataType = 1;
	if (DAQVersion_output >= 20020408 && HM1.use_normal_method) { *output_lmf << TDCDataType; byte_counter += sizeof(__int32); }

	if (DAQ_ID_output == DAQ_ID_HM1 || DAQ_ID_output == DAQ_ID_HM1_ABM) {
		*output_lmf << HM1.Even_open_time; byte_counter += sizeof(__int32);
		*output_lmf << HM1.Auto_Trigger; byte_counter += sizeof(__int32);
	}

	if (DAQVersion_output >= 20080507) {
		unsigned __int64 dummy = number_of_channels_output;
		*output_lmf << dummy; byte_counter += sizeof(__int64);			// number of channels
		if (DAQ_ID_output == DAQ_ID_HM1_ABM) {
			dummy = 0;
			*output_lmf << dummy; byte_counter += sizeof(__int64);
		}
		else {
			dummy = max_number_of_hits_output;
			*output_lmf << dummy; byte_counter += sizeof(__int64);		// number of hits
		}
	}
	else {
		*output_lmf << number_of_channels_output; byte_counter += sizeof(__int32);			// number of channels
		if (DAQ_ID_output == DAQ_ID_HM1_ABM) {
			*output_lmf << __int32(0); byte_counter += sizeof(__int32);
		}
		else {
			*output_lmf << max_number_of_hits_output; byte_counter += sizeof(__int32);			// number of hits
		}
	}

	if (DAQ_ID_output == DAQ_ID_HM1 || DAQ_ID_output == DAQ_ID_HM1_ABM) {
		*output_lmf << HM1.set_bits_for_GP1; byte_counter += sizeof(__int32);
	}
	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);				// data format (2=short integer)

	if (DAQ_ID_output == DAQ_ID_HM1 || DAQ_ID_output == DAQ_ID_HM1_ABM) { *output_lmf << module_2nd;	byte_counter += sizeof(__int32); }	// indicator for 2nd module data

	if (DAQ_ID_output == DAQ_ID_2HM1) {
		*output_lmf << DAQSubVersion;						byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_FAK_DLL_Value;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_Resolution_Flag;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_trigger_mode_for_start;	byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_trigger_mode_for_stop;	byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_res_adjust;				byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_tdcresolution;			byte_counter += sizeof(double);
		*output_lmf << HM1.TWOHM1_test_overflow;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_number_of_channels;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_number_of_hits;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_set_bits_for_GP1;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_HM1_ID_1;					byte_counter += sizeof(__int32);
		*output_lmf << HM1.TWOHM1_HM1_ID_2;					byte_counter += sizeof(__int32);
	}

	if (DAQ_ID_output == DAQ_ID_HM1_ABM) {
		*output_lmf << HM1.ABM_m_xFrom;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_xTo;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_yFrom;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_yTo;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_xMin;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_xMax;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_yMin;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_yMax;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_xOffset;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_yOffset;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_m_zOffset;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_Mode;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_OsziDarkInvert;	byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_ErrorHisto;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_XShift;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_YShift;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_ZShift;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_ozShift;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_wdShift;			byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_ucLevelXY;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_ucLevelZ;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_uiABMXShift;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_uiABMYShift;		byte_counter += sizeof(__int32);
		*output_lmf << HM1.ABM_uiABMZShift;		byte_counter += sizeof(__int32);
	}

	return byte_counter;
}







/////////////////////////////////////////////////////////////////
__int32	LMF_IO::WriteCAMACHeader()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32 byte_counter;
	byte_counter = 0;

	*output_lmf << frequency;	byte_counter += sizeof(double);		// frequency is always 4th value
	*output_lmf << IOaddress;	byte_counter += sizeof(__int32);		// IO address (parameter 1) always 5th value
	*output_lmf << timestamp_format_output;	byte_counter += sizeof(__int32);		// TimeInfo (parameter 2) always 6th value  (0,1,2)*32Bit

	unsigned __int32 dummy = __int32(DAQ_info.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);		// Length of DAQInfo always 7th value
	output_lmf->write(DAQ_info.c_str(), __int32(DAQ_info.length()));	// DAQInfo always 8th value
	byte_counter += __int32(DAQ_info.length());

	dummy = __int32(Camac_CIF.length());
	*output_lmf << dummy;
	byte_counter += sizeof(__int32);
	output_lmf->write(Camac_CIF.c_str(), __int32(Camac_CIF.length()));
	byte_counter += __int32(Camac_CIF.length());

	*output_lmf << system_timeout_output; byte_counter += sizeof(__int32);		// system time-out
	*output_lmf << time_reference_output; byte_counter += sizeof(__int32);
	*output_lmf << data_format_in_userheader_output;	byte_counter += sizeof(__int32);		// data format (2=short integer)

	return byte_counter;
}





bool LMF_IO::OpenOutputLMF(std::string LMF_Filename)
{
	return OpenOutputLMF((__int8*)LMF_Filename.c_str());
}



/////////////////////////////////////////////////////////////////
bool LMF_IO::OpenOutputLMF(__int8* LMF_Filename)
/////////////////////////////////////////////////////////////////
{
	//double				double_Dummy = 0.;
	//unsigned __int32	unsigned_int_Dummy = 0;
	//__int32				int_Dummy = 0;

	if (Parameter_old) memset(Parameter_old, 0, 10000 * sizeof(double));
	for (__int32 i = 901; i <= 932; i++) Parameter_old[i] = -1.e201;

	if (OutputFileIsOpen) {
		errorflag = 12; // file is already open
		return false;
	}
	output_lmf = new MyFILE(false);

	fADC8.at_least_1_signal_was_written = false;

	output_lmf->open(LMF_Filename);

	if (output_lmf->error) {
		errorflag = 11; // could not open output file
		return false;
	}

	//	out_ar = new CArchive(output_lmf,CArchive::store);
	//	if (!out_ar) {
	//		errorflag = 13; // could not connect CAchrive to output file
	//		output_lmf->Close(); output_lmf = 0;
	//		return false;
	//	}

	if (number_of_DAQ_source_strings_output == -1 && number_of_DAQ_source_strings > 0) {
		number_of_DAQ_source_strings_output = number_of_DAQ_source_strings;
		DAQ_source_strings_output = new std::string * [number_of_DAQ_source_strings];
		memset(DAQ_source_strings_output, 0, sizeof(std::string*) * number_of_DAQ_source_strings_output);
		for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) { DAQ_source_strings_output[i] = new std::string(); *DAQ_source_strings_output[i] = *DAQ_source_strings[i]; }
	}
	else number_of_DAQ_source_strings_output = 0;

	if (number_of_CCFHistory_strings_output == -1 && number_of_CCFHistory_strings > 0) {
		number_of_CCFHistory_strings_output = number_of_CCFHistory_strings;
		CCFHistory_strings_output = new std::string * [number_of_CCFHistory_strings];
		memset(CCFHistory_strings_output, 0, sizeof(std::string*) * number_of_CCFHistory_strings_output);
		for (__int32 i = 0; i < number_of_CCFHistory_strings; ++i) { CCFHistory_strings_output[i] = new std::string(); *CCFHistory_strings_output[i] = *CCFHistory_strings[i]; }
	}
	else number_of_CCFHistory_strings_output = 0;

	if (number_of_DAN_source_strings_output == -1 && number_of_DAN_source_strings > 0) {
		number_of_DAN_source_strings_output = number_of_DAN_source_strings;
		DAN_source_strings_output = new std::string * [number_of_DAN_source_strings];
		memset(DAN_source_strings_output, 0, sizeof(std::string*) * number_of_DAN_source_strings_output);
		for (__int32 i = 0; i < number_of_DAN_source_strings; ++i) { DAN_source_strings_output[i] = new std::string(); *DAN_source_strings_output[i] = *DAN_source_strings[i]; }
	}
	else number_of_DAN_source_strings_output = 0;

	if (DAQ_ID_output == DAQ_ID_RAW32BIT) {
		if (number_of_channels_output == 0) number_of_channels_output = number_of_channels;
		if (max_number_of_hits_output == 0) max_number_of_hits_output = max_number_of_hits;
		if (number_of_channels_output == 0 || max_number_of_hits_output == 0) { errorflag = 14; return false; }
		Numberofcoordinates_output = number_of_channels_output * (1 + max_number_of_hits_output);
		data_format_in_userheader_output = 10;

		errorflag = 0; // no error
		OutputFileIsOpen = true;
		return true;
	}

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		if (number_of_channels_output == 0) number_of_channels_output = number_of_channels;
		if (max_number_of_hits_output == 0) max_number_of_hits_output = max_number_of_hits;
		if (number_of_channels_output == 0 || max_number_of_hits_output == 0) { errorflag = 14; return false; }
		Numberofcoordinates_output = number_of_channels_output * (1 + max_number_of_hits_output);
		if (SIMPLE_DAQ_ID_Orignial == 0) SIMPLE_DAQ_ID_Orignial = DAQ_ID;
		*output_lmf << SIMPLE_DAQ_ID_Orignial;
		unsigned __int32 dummy = (unsigned __int32)(uint64_number_of_written_events);
		*output_lmf << dummy;
		*output_lmf << data_format_in_userheader_output;

		errorflag = 0; // no error
		OutputFileIsOpen = true;
		return true;
	}



	// Preparing to write LMF-header:
	// -----------------------------------
	OutputFilePathName = LMF_Filename;

	Headersize_output = 0;

	if (DAQVersion_output == -1) DAQVersion_output = DAQVersion;

	if (DAQVersion_output >= 20080000 && Cobold_Header_version_output == 0) Cobold_Header_version_output = 2008;
	if (Cobold_Header_version_output == 0) Cobold_Header_version_output = Cobold_Header_version;

	if (tdcresolution_output < 0.) tdcresolution_output = tdcresolution;
	if (Starttime_output == 0) {
		Starttime_output = Starttime;
	}
	if (Stoptime_output == 0) {
		Stoptime_output = Stoptime;
	}
	if (system_timeout_output == -1) system_timeout_output = system_timeout;
	if (time_reference_output == 0) time_reference_output = time_reference;
	if (common_mode_output == -1) common_mode_output = common_mode;

	if (number_of_channels_output == 0) number_of_channels_output = number_of_channels;
	if (max_number_of_hits_output == 0) max_number_of_hits_output = max_number_of_hits;

	if (data_format_in_userheader_output == -2) data_format_in_userheader_output = data_format_in_userheader;
	if (DAQ_ID_output == 0) DAQ_ID_output = DAQ_ID;
	if (DAQ_ID_output == DAQ_ID_TDC8HPRAW) DAQ_ID_output = DAQ_ID_TDC8HP;

	if (DAQ_ID_output == DAQ_ID_2TDC8) {
		if (number_of_channels2_output == -1) number_of_channels2_output = number_of_channels2;
		if (max_number_of_hits2_output == -1) max_number_of_hits2_output = max_number_of_hits2;
	}

	if (max_number_of_hits2_output < __int32(0) || max_number_of_hits2_output > __int32(100000)) max_number_of_hits2_output = max_number_of_hits_output;

	if (timestamp_format_output == -1) timestamp_format_output = timestamp_format;

	if (Numberofcoordinates_output == -2) {
		if (data_format_in_userheader_output == LM_SHORT)  Numberofcoordinates_output = timestamp_format_output * 2;
		if (data_format_in_userheader_output == LM_DOUBLE) Numberofcoordinates_output = timestamp_format_output == 0 ? 0 : 1;
		if (data_format_in_userheader_output == LM_SLONG)  Numberofcoordinates_output = timestamp_format_output;
		if (data_format_in_userheader_output == LM_SHORT || data_format_in_userheader_output == LM_DOUBLE || data_format_in_userheader_output == LM_SLONG) {
			Numberofcoordinates_output += number_of_channels_output * (max_number_of_hits_output + 1);
			Numberofcoordinates_output += number_of_channels2_output * (max_number_of_hits2_output + 1);
		}
		if (data_format_in_userheader_output == LM_CAMAC) Numberofcoordinates_output = Numberofcoordinates;

		if (data_format_in_userheader_output == LM_USERDEF) {
			if (DAQVersion_output < 20080000) { this->errorflag = 17; return false; }
			if (DAQ_ID_output == DAQ_ID_TDC8HP) {
				//Numberofcoordinates_output = 2 + timestamp_format_output + number_of_channels_output*(1+max_number_of_hits_output); // old
				Numberofcoordinates_output = number_of_channels_output * (1 + max_number_of_hits_output);
				if (LMF_Version >= 9) Numberofcoordinates_output++; // for level info
			}
			if (DAQ_ID_output == DAQ_ID_TDC8 || DAQ_ID_output == DAQ_ID_2TDC8) {
				//Numberofcoordinates_output = 2 + timestamp_format_output*2 + (number_of_channels_output + number_of_channels2_output)*(1+max_number_of_hits_output); // old
				Numberofcoordinates_output = (number_of_channels_output + number_of_channels2_output) * (1 + max_number_of_hits_output);
			}
			if (DAQ_ID_output == DAQ_ID_HM1) {
				//Numberofcoordinates_output = 2 + timestamp_format_output*2 + (number_of_channels_output + number_of_channels2_output)*(1+max_number_of_hits_output); // old
				Numberofcoordinates_output = (number_of_channels_output + number_of_channels2_output) * (1 + max_number_of_hits_output);
			}
			if (DAQ_ID_output == DAQ_ID_FADC8) {
				Numberofcoordinates_output = 3 * number_of_channels_output * (1 + max_number_of_hits_output);
			}
			if (DAQ_ID_output == DAQ_ID_FADC4) {
				return false;
			}
		}
	}



	//  WRITE LMF-HEADER:


	WriteFirstHeader();

	output_lmf->flush();

	Headersize_output = (unsigned __int32)(output_lmf->tell());

	unsigned __int64 seek_value;
	if (Cobold_Header_version_output <= 2002) seek_value = 3 * sizeof(unsigned __int32);
	if (Cobold_Header_version_output >= 2008) seek_value = 2 * sizeof(unsigned __int32) + sizeof(unsigned __int64);
	output_lmf->seek(seek_value);


	if (Cobold_Header_version_output <= 2002) *output_lmf << Headersize_output;
	if (Cobold_Header_version_output >= 2008) {
		unsigned __int64 temp = Headersize_output;
		*output_lmf << temp;
	}

	output_lmf->flush();
	output_lmf->seek(Headersize_output);

	if (LMF_Version_output == -1) {
		LMF_Version_output = LMF_Version;
		if (LMF_Version_output == -1) LMF_Version_output = 12; // XXX if necessary: modify to latest LMF version number
	}

	output_byte_counter = 0;

	//  WRITE USER-HEADER
	if (Cobold_Header_version_output >= 2008 || DAQVersion_output >= 20080000) {
		*output_lmf << LMF_Header_version;
		output_byte_counter += sizeof(__int32);
	}
	if (Cobold_Header_version_output <= 2002) {
		*output_lmf << User_header_size_output;
		output_byte_counter += sizeof(__int32);
	}
	if (Cobold_Header_version_output >= 2008) {
		unsigned __int64 temp = User_header_size_output;
		*output_lmf << temp;
		output_byte_counter += sizeof(unsigned __int64);
	}

	*output_lmf << DAQVersion_output;			output_byte_counter += sizeof(__int32);	// Version is always 2nd value
	*output_lmf << DAQ_ID_output;		output_byte_counter += sizeof(__int32);	// DAQ_ID is always 3ed value

	if (DAQ_ID_output == DAQ_ID_TDC8)	 output_byte_counter += WriteTDC8PCI2Header();
	if (DAQ_ID_output == DAQ_ID_2TDC8)	 output_byte_counter += Write2TDC8PCI2Header();
	if (DAQ_ID_output == DAQ_ID_TDC8HP || DAQ_ID_output == DAQ_ID_TDC8HPRAW) {
		if (this->LMF_Version_output < 8) output_byte_counter += WriteTDC8HPHeader_LMFV_1_to_7();
		if (this->LMF_Version_output >= 8 && this->LMF_Version_output <= 9) output_byte_counter += WriteTDC8HPHeader_LMFV_8_to_9();
		if (this->LMF_Version_output >= 10) output_byte_counter += WriteTDC8HPHeader_LMFV_10_to_12();
	}

	if (DAQ_ID_output == DAQ_ID_TDC8HQ) {
		printf("Error: Writing TDC8HQ-header is not yet implemented.\n"); // xxx
		return false;
	}

	if (DAQ_ID_output == DAQ_ID_HM1)	 output_byte_counter += WriteHM1Header();
	if (DAQ_ID_output == DAQ_ID_HM1_ABM) output_byte_counter += WriteHM1Header();
	if (DAQ_ID_output == DAQ_ID_CAMAC)   output_byte_counter += WriteCAMACHeader();
	if (DAQ_ID_output == DAQ_ID_TCPIP)   output_byte_counter += WriteTCPIPHeader();
	if (DAQ_ID_output == DAQ_ID_FADC8)   output_byte_counter += WritefADC8_header_LMFversion10();

	User_header_size_output = output_byte_counter;

	errorflag = 0; // no error
	OutputFileIsOpen = true;
	return true;
}











/////////////////////////////////////////////////////////////////
void LMF_IO::WriteFirstHeader()
/////////////////////////////////////////////////////////////////
{
	if (Cobold_Header_version_output >= 2008) {
		unsigned __int32 ArchiveFlagtemp = 476759;

		ArchiveFlagtemp = ArchiveFlagtemp | DAN_SOURCE_CODE;
		ArchiveFlagtemp = ArchiveFlagtemp | DAQ_SOURCE_CODE;
		ArchiveFlagtemp = ArchiveFlagtemp | CCF_HISTORY_CODE;

		*output_lmf << ArchiveFlagtemp;
		*output_lmf << data_format_in_userheader_output;

		unsigned __int64 temp;
		temp = Numberofcoordinates_output;  *output_lmf << temp;
		temp = Headersize_output;			*output_lmf << temp;
		temp = User_header_size_output;		*output_lmf << temp;
		*output_lmf << uint64_number_of_written_events;
	}

	if (Cobold_Header_version_output <= 2002) {
		unsigned __int32 ArchiveFlagtemp = 476758;
		*output_lmf << ArchiveFlagtemp;
		*output_lmf << data_format_in_userheader_output;

		*output_lmf << Numberofcoordinates_output;
		*output_lmf << Headersize_output;
		*output_lmf << User_header_size_output;
		unsigned __int32 dummy = (unsigned __int32)(uint64_number_of_written_events);
		*output_lmf << dummy;
	}

	write_times(output_lmf, Starttime_output, Stoptime_output);

	Write_StdString_as_CString(*output_lmf, Versionstring);
	Write_StdString_as_CString(*output_lmf, OutputFilePathName);
	Write_StdString_as_CString(*output_lmf, Comment_output);

	if (CCFHistory_strings_output) {
		if (number_of_CCFHistory_strings_output > 0) {
			*output_lmf << number_of_CCFHistory_strings_output;
			for (__int32 i = 0; i < number_of_CCFHistory_strings_output; ++i) {
				unsigned __int32 unsigned_int_Dummy = (unsigned __int32)(CCFHistory_strings_output[i]->length());
				*output_lmf << unsigned_int_Dummy;
				output_lmf->write(CCFHistory_strings_output[i]->c_str(), __int32(CCFHistory_strings_output[i]->length()));
			}
		}
		else *output_lmf << __int32(0);
	}
	else {
		number_of_CCFHistory_strings_output = 0;
		if (Cobold_Header_version_output >= 2008) *output_lmf << number_of_CCFHistory_strings_output;
	}

	if (DAN_source_strings_output) {
		if (number_of_DAN_source_strings_output > 0) {
			*output_lmf << number_of_DAN_source_strings_output;
			for (__int32 i = 0; i < number_of_DAN_source_strings_output; ++i) {
				unsigned __int32 unsigned_int_Dummy = (unsigned __int32)(DAN_source_strings_output[i]->length());
				*output_lmf << unsigned_int_Dummy;
				output_lmf->write(DAN_source_strings_output[i]->c_str(), __int32(DAN_source_strings_output[i]->length()));
			}
		}
		else *output_lmf << __int32(0);
	}
	else {
		number_of_DAN_source_strings_output = 0;
		if (Cobold_Header_version_output >= 2008) *output_lmf << number_of_DAN_source_strings_output;
	}
}














/////////////////////////////////////////////////////////////////
void LMF_IO::WriteEventHeader(unsigned __int64 timestamp, unsigned __int32 cnt[])
/////////////////////////////////////////////////////////////////
{
	unsigned __int64 HeaderLength = 0;
	// EventLength information in 64Bit
	if (DAQVersion_output >= 20080000 || data_format_in_userheader_output == LM_USERDEF) {
		HeaderLength = timestamp_format_output + 1 + number_of_channels_output;	// +1 for HeaderLength itself

		HeaderLength = timestamp_format_output * sizeof(__int32) + 2 * sizeof(__int64);	// +2 for HeaderLength itself, +2 for EventCounter (size in __int32)
		for (__int32 iCount = 0; iCount < number_of_channels_output; ++iCount) HeaderLength += cnt[iCount] * sizeof(__int32);
		HeaderLength += number_of_channels_output * sizeof(__int16);
#ifdef LINUX
		HeaderLength = (HeaderLength & 0x00ffffffffffffffLL) | 0xff00000000000000LL;	// set 0xff in bits 63..56 as EventMarker
#else
		HeaderLength = (HeaderLength & 0x00ffffffffffffff) | 0xff00000000000000;	// set 0xff in bits 63..56 as EventMarker
#endif
		* output_lmf << HeaderLength;
		*output_lmf << uint64_number_of_written_events;
	}

	myLARGE_INTEGER LARGE_Timestamp;
	LARGE_Timestamp.QuadPart = timestamp;

	if (timestamp_format_output > 0) {
		*output_lmf << LARGE_Timestamp.LowPart;
		if (timestamp_format_output == 2) *output_lmf << LARGE_Timestamp.HighPart;
	}
}













/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(unsigned __int64 timestamp, unsigned __int32 cnt[], __int32* i32TDC)
/////////////////////////////////////////////////////////////////
{
	unsigned __int16 dummy_uint16;
	__int32 dummy_int32;
	double dummy_double;

	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	++uint64_number_of_written_events;

	WriteEventHeader(timestamp, cnt);

	__int32 i, j;
	if (DAQ_ID_output != DAQ_ID_SIMPLE) {
		for (i = 0; i < number_of_channels_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits_output) hits = max_number_of_hits_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(i32TDC[i * num_ions + j]);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = (unsigned __int16)(0);
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) {
					dummy_double = double(i32TDC[i * max_number_of_hits_output + j]);
					*output_lmf << dummy_double;
				}
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				*output_lmf << __int32(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));
				for (j = 0; j < hits; ++j) *output_lmf << i32TDC[i * max_number_of_hits_output + j];
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_int32;
			}
			if (data_format_in_userheader_output == LM_USERDEF) {
				dummy_uint16 = (unsigned __int16)(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));
				*output_lmf << dummy_uint16;
				if (DAQ_ID_output == DAQ_ID_2TDC8 || DAQ_ID_output == DAQ_ID_TDC8 || DAQ_ID_output == DAQ_ID_HM1) {
					for (j = 0; j < hits; ++j) {
						dummy_uint16 = (unsigned __int16)(i32TDC[i * max_number_of_hits_output + j]);
						*output_lmf << dummy_uint16;
					}
				}
				else {
					for (j = 0; j < hits; ++j)
						*output_lmf << i32TDC[i * max_number_of_hits_output + j];
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 9) {
			*output_lmf << ui64LevelInfo;
		}

		if (this->LMF_Version_output >= 11) {
			unsigned __int32 changed_mask = 0;
			//__int32 max_par_index = 932;
			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					changed_mask += (1 << i);
				}
			}

			*output_lmf << changed_mask;

			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					*output_lmf << Parameter[i + 901];
					Parameter_old[i + 901] = Parameter[i + 901];
				}
			}
		}

		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 10) {
			*output_lmf << number_of_bytes_in_PostEventData;
			for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) *output_lmf << ui8_PostEventData[i];
		}
	}
	if (DAQ_ID_output == DAQ_ID_2TDC8 && number_of_channels2_output > 0) { // here we write only the stuff for the second TDC (because the first TDC was written above)
		for (i = number_of_channels_output; i < number_of_channels2_output + number_of_channels_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits2_output) hits = max_number_of_hits2_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));  *output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(i32TDC[i * max_number_of_hits_output + j]);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));		*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) {
					dummy_double = double(i32TDC[i * max_number_of_hits_output + j]);
					*output_lmf << dummy_double;
				}
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				dummy_int32 = __int32(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));		*output_lmf << dummy_int32;
				for (j = 0; j < hits; ++j) *output_lmf << i32TDC[i * max_number_of_hits_output + j];
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_int32;
			}
			if (data_format_in_userheader_output == LM_USERDEF) {
				dummy_uint16 = (unsigned __int16)(hits + (DAQ_ID == DAQ_ID_HM1 ? 1 : 0));
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(i32TDC[i * max_number_of_hits_output + j]);
					*output_lmf << dummy_uint16;
				}
			}
		}
	}

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		unsigned __int32 channel;
		unsigned __int32 i;
		i = 0;
		for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) i = i + cnt[channel] + (cnt[channel] > 0 ? 1 : 0);
		if (data_format_in_userheader_output == 2) { dummy_uint16 = (unsigned __int16)i; *output_lmf << dummy_uint16; }
		if (data_format_in_userheader_output == 10) *output_lmf << i;
		if (data_format_in_userheader_output == 2) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_uint16 = (unsigned __int16)((channel << 8) + cnt[channel]);
					*output_lmf << dummy_uint16;
					for (i = 0; i < cnt[channel]; ++i) {
						dummy_uint16 = (unsigned __int16)(i32TDC[channel * max_number_of_hits_output + i]);
						*output_lmf << dummy_uint16;
					}
				}
			}
		}
		if (data_format_in_userheader_output == 10) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_int32 = __int32((channel << 24) + cnt[channel]);
					*output_lmf << dummy_int32;
					for (i = 0; i < cnt[channel]; ++i) *output_lmf << i32TDC[channel * max_number_of_hits_output + i];
				}
			}
		}
	} // end if (DAQ_ID_output == DAQ_ID_SIMPLE)

	// xxx TODO Write TDC4HM data

	return;
}



/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(double timestamp, unsigned __int32 cnt[], __int32* i32TDC)
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	unsigned __int64 new_timestamp = (unsigned __int64)(timestamp * frequency + 0.001);

	WriteTDCData(new_timestamp, cnt, i32TDC);

	return;
}












/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(unsigned __int64 timestamp, unsigned __int32 cnt[], double* d64TDC)
/////////////////////////////////////////////////////////////////
{
	unsigned __int16 dummy_uint16;
	double dummy_double;
	__int32 dummy_int32;

	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	++uint64_number_of_written_events;

	WriteEventHeader(timestamp, cnt);

	__int32 i, j;
	__int32 ii;
	if (DAQ_ID_output != DAQ_ID_SIMPLE) {
		for (i = 0; i < number_of_channels_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits_output) hits = max_number_of_hits_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(d64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) 	*output_lmf << d64TDC[i * max_number_of_hits_output + j];
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				dummy_int32 = __int32(hits);
				*output_lmf << dummy_int32;
				for (j = 0; j < hits; ++j) {
					if (d64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (d64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					*output_lmf << ii;
				}
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_int32;
			}
			if (data_format_in_userheader_output == LM_USERDEF) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					if (d64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (d64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					if (DAQ_ID_output != DAQ_ID_HM1 && DAQ_ID_output != DAQ_ID_TDC8 && DAQ_ID_output != DAQ_ID_2TDC8) *output_lmf << ii;
					else *output_lmf << (unsigned __int16)(ii);
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 9) {
			*output_lmf << ui64LevelInfo;
		}
		if (this->LMF_Version_output >= 11) {
			unsigned __int32 changed_mask = 0;
			//__int32 max_par_index = 932;
			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					changed_mask += (1 << i);
				}
			}

			*output_lmf << changed_mask;

			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					*output_lmf << Parameter[i + 901];
					Parameter_old[i + 901] = Parameter[i + 901];
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 10) {
			*output_lmf << number_of_bytes_in_PostEventData;
			for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) *output_lmf << ui8_PostEventData[i];
		}
	}
	if (DAQ_ID_output == DAQ_ID_2TDC8 && number_of_channels2_output > 0) {
		for (i = number_of_channels_output; i < number_of_channels_output + number_of_channels2_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits2_output) hits = max_number_of_hits2_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(d64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) *output_lmf << d64TDC[i * max_number_of_hits_output + j];
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				*output_lmf << __int32(hits);
				for (j = 0; j < hits; ++j) {
					if (d64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (d64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(d64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					*output_lmf << ii;
				}
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_int32;
			}
		}
	}

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		unsigned __int32 channel;
		unsigned __int32 i;
		i = 0;
		for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) i = i + cnt[channel] + (cnt[channel] > 0 ? 1 : 0);
		if (data_format_in_userheader_output == 2) {
			dummy_uint16 = (unsigned __int16)i;
			*output_lmf << dummy_uint16;
		}
		if (data_format_in_userheader_output == 10) *output_lmf << i;
		if (data_format_in_userheader_output == 2) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_uint16 = (unsigned __int16)((channel << 8) + cnt[channel]);
					*output_lmf << dummy_uint16;
					for (i = 0; i < cnt[channel]; ++i) {
						dummy_uint16 = (unsigned __int16)(d64TDC[channel * max_number_of_hits_output + i]);
						*output_lmf << dummy_uint16;
					}
				}
			}
		}
		if (data_format_in_userheader_output == 10) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_int32 = __int32((channel << 24) + cnt[channel]);
					*output_lmf << dummy_int32;
					for (i = 0; i < cnt[channel]; ++i) {
						dummy_int32 = __int32(d64TDC[channel * max_number_of_hits_output + i]);
						*output_lmf << dummy_int32;
					}
				}
			}
		}
	} // end if (DAQ_ID_output == DAQ_ID_SIMPLE)

	return;
}

/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(double timestamp, unsigned __int32 cnt[], double* dtdc)
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}
	unsigned __int64 new_timestamp = (unsigned __int64)(timestamp * frequency + 0.001);

	WriteTDCData(new_timestamp, cnt, dtdc);

	return;
}






/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(unsigned __int64 timestamp, unsigned __int32 cnt[], __int64* i64TDC)
/////////////////////////////////////////////////////////////////
{
	unsigned __int16 dummy_uint16;
	double dummy_double;
	__int32 dummy_int32;

	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	++uint64_number_of_written_events;

	WriteEventHeader(timestamp, cnt);

	__int32 i, j;
	__int32 ii;
	if (DAQ_ID_output != DAQ_ID_SIMPLE) {
		for (i = 0; i < number_of_channels_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits_output) hits = max_number_of_hits_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(i64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) 	*output_lmf << double(i64TDC[i * max_number_of_hits_output + j]);
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				dummy_int32 = __int32(hits);
				*output_lmf << dummy_int32;
				for (j = 0; j < hits; ++j) {
					if (i64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (i64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					*output_lmf << ii;
				}
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_int32;
			}
			if (data_format_in_userheader_output == LM_USERDEF) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					if (i64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (i64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					if (DAQ_ID_output != DAQ_ID_HM1 && DAQ_ID_output != DAQ_ID_TDC8 && DAQ_ID_output != DAQ_ID_2TDC8) *output_lmf << ii;
					else *output_lmf << (unsigned __int16)(ii);
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 9) {
			*output_lmf << ui64LevelInfo;
		}
		if (this->LMF_Version_output >= 11) {
			unsigned __int32 changed_mask = 0;
			//__int32 max_par_index = 932;
			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					changed_mask += (1 << i);
				}
			}

			*output_lmf << changed_mask;

			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					*output_lmf << Parameter[i + 901];
					Parameter_old[i + 901] = Parameter[i + 901];
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 10) {
			*output_lmf << number_of_bytes_in_PostEventData;
			for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) *output_lmf << ui8_PostEventData[i];
		}
	}
	if (DAQ_ID_output == DAQ_ID_2TDC8 && number_of_channels2_output > 0) {
		for (i = number_of_channels_output; i < number_of_channels_output + number_of_channels2_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits2_output) hits = max_number_of_hits2_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_uint16 = (unsigned __int16)(i64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					*output_lmf << dummy_uint16;
				}
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) *output_lmf << i64TDC[i * max_number_of_hits_output + j];
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				*output_lmf << __int32(hits);
				for (j = 0; j < hits; ++j) {
					if (i64TDC[i * max_number_of_hits_output + j] >= 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] + 1.e-6);
					if (i64TDC[i * max_number_of_hits_output + j] < 0.) ii = __int32(i64TDC[i * max_number_of_hits_output + j] - 1.e-6);
					*output_lmf << ii;
				}
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_int32;
			}
		}
	}

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		unsigned __int32 channel;
		unsigned __int32 i;
		i = 0;
		for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) i = i + cnt[channel] + (cnt[channel] > 0 ? 1 : 0);
		if (data_format_in_userheader_output == 2) {
			dummy_uint16 = (unsigned __int16)i;
			*output_lmf << dummy_uint16;
		}
		if (data_format_in_userheader_output == 10) *output_lmf << i;
		if (data_format_in_userheader_output == 2) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_uint16 = (unsigned __int16)((channel << 8) + cnt[channel]);
					*output_lmf << dummy_uint16;
					for (i = 0; i < cnt[channel]; ++i) {
						dummy_uint16 = (unsigned __int16)(i64TDC[channel * max_number_of_hits_output + i]);
						*output_lmf << dummy_uint16;
					}
				}
			}
		}
		if (data_format_in_userheader_output == 10) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_int32 = __int32((channel << 24) + cnt[channel]);
					*output_lmf << dummy_int32;
					for (i = 0; i < cnt[channel]; ++i) {
						dummy_int32 = __int32(i64TDC[channel * max_number_of_hits_output + i]);
						*output_lmf << dummy_int32;
					}
				}
			}
		}
	} // end if (DAQ_ID_output == DAQ_ID_SIMPLE)

	return;
}

/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(double timestamp, unsigned __int32 cnt[], __int64* i64tdc)
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}
	unsigned __int64 new_timestamp = (unsigned __int64)(timestamp * frequency + 0.001);

	WriteTDCData(new_timestamp, cnt, i64tdc);

	return;
}










/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(unsigned __int64 timestamp, unsigned __int32 cnt[], unsigned __int16* us16TDC)
/////////////////////////////////////////////////////////////////
{
	unsigned __int16 dummy_uint16;
	double dummy_double;
	__int32 dummy_int32;


	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	++uint64_number_of_written_events;

	WriteEventHeader(timestamp, cnt);

	__int32 i, j;

	if (DAQ_ID_output == DAQ_ID_HM1_ABM) {
		for (i = 0; i < number_of_channels_output; ++i) {
			if (data_format_in_userheader_output == 2)  *output_lmf << us16TDC[i * max_number_of_hits_output];
			if (data_format_in_userheader_output == 5) { dummy_double = double(us16TDC[i * max_number_of_hits_output]); *output_lmf << dummy_double; }
			if (data_format_in_userheader_output == 10) { dummy_int32 = __int32(us16TDC[i * max_number_of_hits_output]); *output_lmf << dummy_int32; }
		}
	}
	if (DAQ_ID_output != DAQ_ID_SIMPLE && DAQ_ID_output != DAQ_ID_HM1_ABM) {
		for (i = 0; i < number_of_channels_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits_output) hits = max_number_of_hits_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) *output_lmf << us16TDC[i * max_number_of_hits_output + j];
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) { dummy_double = double(us16TDC[i * max_number_of_hits_output + j]); *output_lmf << dummy_double; }
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				*output_lmf << __int32(hits);
				for (j = 0; j < hits; ++j) { dummy_int32 = __int32(us16TDC[i * max_number_of_hits_output + j]); *output_lmf << dummy_int32; }
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits_output; ++j) *output_lmf << dummy_int32;
			}
			if (data_format_in_userheader_output == LM_USERDEF) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) {
					dummy_int32 = __int32(us16TDC[i * max_number_of_hits_output + j]);
					if (DAQ_ID_output != DAQ_ID_HM1 && DAQ_ID_output != DAQ_ID_TDC8 && DAQ_ID_output != DAQ_ID_2TDC8) *output_lmf << dummy_int32;
					else *output_lmf << (unsigned __int16)(dummy_int32);
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 9) {
			*output_lmf << ui64LevelInfo;
		}
		if (this->LMF_Version_output >= 11) {
			unsigned __int32 changed_mask = 0;
			//__int32 max_par_index = 932;
			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					changed_mask += (1 << i);
				}
			}

			*output_lmf << changed_mask;

			for (__int32 i = 0; i < 32; i++) {
				if (Parameter_old[i + 901] != Parameter[i + 901]) {
					*output_lmf << Parameter[i + 901];
					Parameter_old[i + 901] = Parameter[i + 901];
				}
			}
		}
		if (DAQ_ID_output == DAQ_ID_TDC8HP && this->LMF_Version_output >= 10) {
			*output_lmf << number_of_bytes_in_PostEventData;
			for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) *output_lmf << ui8_PostEventData[i];
		}
	}

	if (DAQ_ID_output == DAQ_ID_2TDC8 && number_of_channels2_output > 0) {
		for (i = number_of_channels_output; i < number_of_channels_output + number_of_channels2_output; ++i) {
			__int32 hits = cnt[i];
			if (hits > max_number_of_hits2_output) hits = max_number_of_hits2_output;
			if (data_format_in_userheader_output == 2) {
				dummy_uint16 = (unsigned __int16)(hits);
				*output_lmf << dummy_uint16;
				for (j = 0; j < hits; ++j) *output_lmf << us16TDC[i * max_number_of_hits_output + j];
				dummy_uint16 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_uint16;
			}
			if (data_format_in_userheader_output == 5) {
				dummy_double = double(hits);
				*output_lmf << dummy_double;
				for (j = 0; j < hits; ++j) { dummy_double = double(us16TDC[i * max_number_of_hits_output + j]); *output_lmf << dummy_double; }
				dummy_double = 0.;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_double;
			}
			if (data_format_in_userheader_output == 10) {
				dummy_int32 = __int32(hits);
				*output_lmf << dummy_int32;
				for (j = 0; j < hits; ++j) { dummy_int32 = __int32(us16TDC[i * max_number_of_hits_output + j]); *output_lmf << dummy_int32; }
				dummy_int32 = 0;
				for (j = hits; j < max_number_of_hits2_output; ++j) *output_lmf << dummy_int32;
			}
		}
	}

	if (DAQ_ID_output == DAQ_ID_SIMPLE) {
		unsigned __int32 channel;
		unsigned __int32 i = 0;

		for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) i = i + cnt[channel] + (cnt[channel] > 0 ? 1 : 0);
		if (data_format_in_userheader_output == 2) { dummy_uint16 = (unsigned __int16)i; *output_lmf << dummy_uint16; }
		if (data_format_in_userheader_output == 10) *output_lmf << i;
		if (data_format_in_userheader_output == 2) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_uint16 = (unsigned __int16)((channel << 8) + cnt[channel]);
					*output_lmf << dummy_uint16;
					for (i = 0; i < cnt[channel]; ++i) *output_lmf << us16TDC[channel * max_number_of_hits_output + i];
				}
			}
		}
		if (data_format_in_userheader_output == 10) {
			for (channel = 0; channel < (unsigned __int32)number_of_channels_output; ++channel) {
				if (cnt[channel] > 0) {
					dummy_int32 = __int32((channel << 24) + cnt[channel]);
					*output_lmf << dummy_int32;
					for (i = 0; i < cnt[channel]; ++i) { dummy_int32 = __int32(us16TDC[channel * max_number_of_hits_output + i]); *output_lmf << dummy_int32; }
				}
			}
		}
	} // end if (DAQ_ID_output == DAQ_ID_SIMPLE)

	return;
}







/////////////////////////////////////////////////////////////////
void LMF_IO::WriteTDCData(double timestamp, unsigned __int32 cnt[], unsigned __int16* us16TDC)
/////////////////////////////////////////////////////////////////
{
	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}
	unsigned __int64 new_timestamp = (unsigned __int64)(timestamp * frequency);

	WriteTDCData(new_timestamp, cnt, us16TDC);

	return;
}








/////////////////////////////////////////////////////////////////
__int32 LMF_IO::GetErrorStatus()
/////////////////////////////////////////////////////////////////
{
	return errorflag;
}







/////////////////////////////////////////////////////////////////
bool LMF_IO::SeekToEventNumber(unsigned __int64 target_number)
/////////////////////////////////////////////////////////////////
{
	if (DAQ_ID == DAQ_ID_SIMPLE) return false;

	if (target_number == 0) {
		input_lmf->seek((unsigned __int64)(Headersize + User_header_size));
		must_read_first = true;
		errorflag = 0;
		input_lmf->error = 0;
		return true;
	}

	if (data_format_in_userheader == LM_USERDEF) { errorflag = 16; return false; }

	if (!input_lmf) {
		errorflag = 9;
		return false;
	}


	/*	unsigned __int64 filesize;
		unsigned __int64 pos = input_lmf->tell();
		input_lmf->seek_to_end();
		filesize = input_lmf->tell();
		input_lmf->seek(pos);
	*/



	if (target_number < 0) return false;
	if (target_number > uint64_Numberofevents) return false;
	__int32 eventsize;
	if (data_format_in_userheader == 2) eventsize = 2 * Numberofcoordinates;
	if (data_format_in_userheader == 5) eventsize = 8 * Numberofcoordinates;
	if (data_format_in_userheader == 10) eventsize = 4 * Numberofcoordinates;

	if (DAQ_ID == DAQ_ID_RAW32BIT) eventsize = 4 * number_of_channels * (max_number_of_hits + 1);

	if (input_lmf->filesize < (unsigned __int64)(eventsize)*target_number + (unsigned  __int64)(Headersize + User_header_size)) return false;

	unsigned __int64 new_position = (unsigned __int64)(eventsize)*target_number + (unsigned __int64)(Headersize + User_header_size);

	input_lmf->seek(new_position);



	uint64_number_of_read_events = target_number;
	must_read_first = true;
	errorflag = 0;
	input_lmf->error = 0;
	return true;
}







///////////////////////////////////////////////////////////////////////////////////
__int32 LMF_IO::PCIGetTDC_TDC8HP_25psGroupMode(unsigned __int64& ref_ui64TDC8HPAbsoluteTimeStamp, __int32 count, unsigned __int32* Buffer)
///////////////////////////////////////////////////////////////////////////////////
{
	memset(number_of_hits, 0, num_channels * sizeof(__int32));		// clear the hit-counts values in _TDC array

	unsigned __int32 ui32DataWord;
	bool bOKFlag = false;
	unsigned __int8 ucTDCChannel;

	for (__int32 i = 0; i < count; ++i)
	{
		ui32DataWord = Buffer[i];
		if ((ui32DataWord & 0xf8000000) == 0x18000000) // handle output level info
		{
			__int32 n = ui32DataWord & 0x7e00000;
			n >>= 21;
			unsigned __int64 ui64_temp_LevelInfo = ui32DataWord & 0x1fffff;
			if (n > 20) continue;
			if (n < 9) ui64_temp_LevelInfo >>= (9 - n); else ui64_temp_LevelInfo <<= (n - 9);

			n -= 9;
			if (n < 0) n = 0;

			unsigned __int64 ui64_tempL_LevelInfo = ui64LevelInfo >> (n + 21);
			ui64_tempL_LevelInfo <<= (n + 21);
			unsigned __int64 ui64_tempR_LevelInfo = n != 0 ? ui64LevelInfo << (64 - n) : 0;
			ui64_tempR_LevelInfo = n != 0 ? ui64_tempR_LevelInfo >> (64 - n) : 0;

			//unsigned __int64 old = ui64LevelInfo;
			ui64LevelInfo = ui64_tempL_LevelInfo | ui64_tempR_LevelInfo | ui64_temp_LevelInfo;

			continue;
		}
		if ((ui32DataWord & 0xC0000000) > 0x40000000)		// valid data only if rising or falling trigger indicated
		{
			__int32 lTDCData = (ui32DataWord & 0x00FFFFFF);
			if (lTDCData & 0x00800000)				// detect 24 bit signed flag
				lTDCData |= 0xff000000;				// if detected extend negative value to 32 bit
			if (!this->TDC8HP.VHR_25ps) 				// correct for 100ps if necessary
				lTDCData >>= 2;

			ucTDCChannel = (unsigned __int8)((ui32DataWord & 0x3F000000) >> 24);		// extract channel information
			// calculate TDC channel to _TDC channel
			bool valid = false;
			if ((ucTDCChannel > 41) && (ucTDCChannel < 51)) {
				ucTDCChannel -= 25; // info: this overwrites the lowres-channel of the 2nd TDC8HP-card
				valid = true;
			}
			else if ((ucTDCChannel > 20) && (ucTDCChannel < 30)) {
				ucTDCChannel -= 12;
				valid = true;
			}
			else if ((ucTDCChannel >= 0) && (ucTDCChannel < 9)) {
				valid = true;
			}

			if (valid) {
				bool bIsFalling = true;
				if ((ui32DataWord & 0xC0000000) == 0xC0000000) bIsFalling = false;

				if (!bIsFalling) {
					ucTDCChannel += TDC8HP.channel_offset_for_rising_transitions;
				}

				if (ucTDCChannel < num_channels)	// if detected channel fits into TDC array then sort
				{
					++number_of_hits[ucTDCChannel];
					__int32 cnt = number_of_hits[ucTDCChannel];
					// increase Hit Counter;

					// test for oversized Hits
					if (cnt > num_ions) {
						--number_of_hits[ucTDCChannel];
						--cnt;
					}
					else {
						// if Hit # ok then store it
						i32TDC[ucTDCChannel * num_ions + cnt - 1] = lTDCData;
						bIsFallingTDC[ucTDCChannel * num_ions + cnt - 1] = bIsFalling;
					}
					bOKFlag = true;
				}
			}
		}
		else
		{
			if ((ui32DataWord & 0xf0000000) == 0x00000000) {			// GroupWord detected
				this->TDC8HP.ui32AbsoluteTimeStamp = ui32DataWord & 0x00ffffff;
			}
			else if ((ui32DataWord & 0xff000000) == 0x10000000) {			// RollOverWord detected ?
				unsigned __int32 ui32newRollOver = (ui32DataWord & 0x00ffffff);
				if (ui32newRollOver > this->TDC8HP.ui32oldRollOver) {
					this->TDC8HP.ui64RollOvers += ui32newRollOver - this->TDC8HP.ui32oldRollOver;
				}
				else if (ui32newRollOver < this->TDC8HP.ui32oldRollOver) {
					this->TDC8HP.ui64RollOvers += ui32newRollOver;
					this->TDC8HP.ui64RollOvers += 1;
					this->TDC8HP.ui64RollOvers += (unsigned __int32)(0x00ffffff) - this->TDC8HP.ui32oldRollOver;
				}
				this->TDC8HP.ui32oldRollOver = ui32newRollOver;
			}
			//	only for debugging:
#ifdef _DEBUG
			else if (((ui32DataWord & 0xc0000000) >> 30) == 0x00000001)			// ErrorWord detected ?
			{
				__int32 channel = (ui32DataWord & 0x3f000000) >> 24;
				__int32 error = (ui32DataWord & 0x00ff0000) >> 16;
				__int32 count = ui32DataWord & 0x0000ffff;
			}
#endif

		}
	}

	if (bOKFlag)
	{
		ref_ui64TDC8HPAbsoluteTimeStamp = this->TDC8HP.ui64RollOvers * (unsigned __int64)(0x0000000001000000);
		ref_ui64TDC8HPAbsoluteTimeStamp += (unsigned __int64)(this->TDC8HP.ui32AbsoluteTimeStamp);
		this->TDC8HP.ui64TDC8HP_AbsoluteTimeStamp = ref_ui64TDC8HPAbsoluteTimeStamp;
	}

	return bOKFlag;
}







/////////////////////////////////////////////////////////////////
bool LMF_IO::Read_TDC8HP_raw_format(unsigned __int64& ui64TDC8HP_AbsoluteTimeStamp_)
/////////////////////////////////////////////////////////////////
{
	__int32 count;
	*input_lmf >> count;
	if (input_lmf->error) return false;
	if (!count) return false;
	if (ui32buffer_size < count) {
		if (ui32buffer) { delete[] ui32buffer; ui32buffer = 0; }
		ui32buffer_size = count + 5000;
		ui32buffer = new unsigned __int32[ui32buffer_size];
	}
	input_lmf->read(this->ui32buffer, count * sizeof(__int32));
	if (input_lmf->error) return false;
	if (!PCIGetTDC_TDC8HP_25psGroupMode(ui64TDC8HP_AbsoluteTimeStamp_, count, this->ui32buffer)) return false;
	return true;
}










/////////////////////////////////////////////////////////////////
bool LMF_IO::ReadNextTDC8HQEvent()
/////////////////////////////////////////////////////////////////
{
	__int32				int_Dummy;
	__int16				i16Dummy;
	__int64				i64Dummy;

	memset(i64TDC, 0, num_channels * num_ions * 8);
	memset(number_of_hits, 0, num_channels * 4);

	if (!input_lmf) {
		errorflag = 9;
		return false;
	}

	if (max_number_of_hits == 0 || number_of_channels == 0) {
		errorflag = 14;
		return false;
	}

	if (input_lmf->error) {
		if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
		return false;
	}


	unsigned __int32 ui32dummy = 0;
	*input_lmf >> ui32dummy;
	if (ui32dummy != 0xdeadface) {
		if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
		return false;
	}


	*input_lmf >> uint64_LMF_EventCounter;											// process i64DAqEventCounter


	myLARGE_INTEGER aaa;
	*input_lmf >> aaa.QuadPart;
	ui64_timestamp = aaa.QuadPart;
	DOUBLE_timestamp = double(ui64_timestamp) / frequency;  // time stamp in seconds.			

	unsigned __int32 changed_mask;
	*input_lmf >> changed_mask;
	if (changed_mask)
	{
		for (__int32 i = 0; i < 32; i++)
		{
			if (!changed_mask)
				break;
			if (changed_mask & 0x1)
			{
				double double_temp;
				*input_lmf >> double_temp;
				Parameter[901 + i] = double_temp;
			}
			changed_mask >>= 1;
		}
	}

	for (unsigned __int32 iChan = 0; iChan < number_of_channels; ++iChan)	// now read the data
	{
		unsigned __int16 n;
		*input_lmf >> n;														// store hits for this channel
		number_of_hits[iChan] = n;
		if (!n)
			continue;

		unsigned __int8 bit_mask = 0;
		for (__int32 nCount = 0; nCount < n; ++nCount)				// transfer selected hits
		{
			unsigned __int32 counter = (nCount % 4) * 2;
			if (!counter)
				*input_lmf >> bit_mask;

			if (bit_mask & (0x1ul << counter))
			{
				if (bit_mask & (0x1ul << (counter + 1)))
				{
					*input_lmf >> i64Dummy;
				}
				else {
					*input_lmf >> int_Dummy;
					i64Dummy = int_Dummy;
				}
			}
			else {
				*input_lmf >> i16Dummy;
				i64Dummy = i16Dummy;
			}
			if (nCount < num_ions)
				i64TDC[iChan * num_ions + nCount] = i64Dummy;
		}
		if (__int32(number_of_hits[iChan]) > num_ions)
			number_of_hits[iChan] = num_ions;
	}

	unsigned __int32 ui32LevelInfo;
	*input_lmf >> ui32LevelInfo;

	// ADC values:
	unsigned __int8 nof_ADC;
	*input_lmf >> nof_ADC;
	for (__int32 i = 0; i < nof_ADC; i++)
	{
		*input_lmf >> i16Dummy;
		if (i < 5)
			i32ADCCounter[i] = i16Dummy; // number of ADC signals
		__int32 n_max = i16Dummy;
		for (__int32 n = 0; n < n_max; n++)
		{
			*input_lmf >> i16Dummy;
			if (i < 5 && n < num_ions)
				i32ADCValue[i * num_ions + n] = i16Dummy; //  ADC value
		}
	}

	unsigned __int32 ui32NumberOfBytestoFollow;
	*input_lmf >> ui32NumberOfBytestoFollow;
	char char_dummy;
	for (unsigned __int32 i = 0; i < ui32NumberOfBytestoFollow; i++)
		*input_lmf >> char_dummy;

	++uint64_number_of_read_events;
	must_read_first = false;
	return true;
}





/////////////////////////////////////////////////////////////////
bool LMF_IO::ReadNextEvent()
/////////////////////////////////////////////////////////////////
{
	unsigned __int32	i, j;
	__int32				int_Dummy;
	unsigned __int16	unsigned_short_Dummy;
	double			double_Dummy;

	if (DAQ_ID == DAQ_ID_TDC8HQ)
		return ReadNextTDC8HQEvent();

	if (!input_lmf) {
		errorflag = 9;
		return false;
	}
	if (DAQ_ID != DAQ_ID_SIMPLE) {
		if ((max_number_of_hits == 0 || number_of_channels == 0) && (DAQ_ID != DAQ_ID_CAMAC)) {
			errorflag = 14;
			return false;
		}
		if ((data_format_in_userheader == LM_CAMAC) && (DAQ_ID == DAQ_ID_CAMAC)) {
			printf("we are here\n");
		}
	}

	if (input_lmf->error) {
		if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1;
		return false;
	}

	if (data_format_in_userheader == 2) memset(us16TDC, 0, num_channels * num_ions * 2);
	if (data_format_in_userheader == 5) memset(dTDC, 0, num_channels * num_ions * 8);
	if (data_format_in_userheader == 10) memset(i32TDC, 0, num_channels * num_ions * 4);
	if (TDC8HP.variable_event_length == 1) memset(i32TDC, 0, num_channels * num_ions * 4);
	if (TDC8PCI2.variable_event_length == 1) memset(us16TDC, 0, num_channels * num_ions * 2);

	unsigned __int64 HPTDC_event_length = 0;
	unsigned __int64 TDC8PCI2_event_length = 0;

	DOUBLE_timestamp = 0.;
	ui64_timestamp = 0;

	if (TDC8HP.variable_event_length == 1) {
		if (this->TDC8HP.UserHeaderVersion >= 5 && this->TDC8HP.GroupingEnable_p66) {

			while (!Read_TDC8HP_raw_format(ui64_timestamp)) {
				if (input_lmf->error) break;
			}
			if (this->LMF_Version >= 11) {
				changed_mask_read = 0;
				*input_lmf >> changed_mask_read;
				unsigned __int32 changed_mask = changed_mask_read;
				if (changed_mask) {
					for (__int32 i = 0; i < 32; i++) {
						if (changed_mask & 0x1) {
							double double_temp;
							*input_lmf >> double_temp;
							Parameter[901 + i] = double_temp;
						}
						changed_mask >>= 1;
					}
				}
			}
			number_of_bytes_in_PostEventData = 0;
			if (this->TDC8HP.UserHeaderVersion >= 7) {
				*input_lmf >> number_of_bytes_in_PostEventData;
				if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
					input_lmf->error = 21;
					return false;
				}
				for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
					unsigned __int8 byte_dummy;
					*input_lmf >> byte_dummy;
					ui8_PostEventData[i] = byte_dummy;
				}
			}

			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
			++uint64_number_of_read_events;
			DOUBLE_timestamp = double(ui64_timestamp) / frequency;  // time stamp in seconds.
			must_read_first = false;
			return true;
		}
		if (!TDC8HP.exotic_file_type) {
			*input_lmf >> HPTDC_event_length;
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }

#ifdef LINUX
			if ((HPTDC_event_length & 0xff00000000000000LL) != 0xff00000000000000LL) {
#else
			if ((HPTDC_event_length & 0xff00000000000000) != 0xff00000000000000) {
#endif
				this->errorflag = 2;
				return false;
			}

#ifdef LINUX
			HPTDC_event_length = HPTDC_event_length & 0x00ffffffffffffffLL;
#else
			HPTDC_event_length = HPTDC_event_length & 0x00ffffffffffffff;
#endif

			* input_lmf >> uint64_LMF_EventCounter;
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
			}
		else {
			__int32 i32HPTDC_event_length;
			*input_lmf >> i32HPTDC_event_length;
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
		}
		}

	if (TDC8PCI2.variable_event_length == 1) {
		*input_lmf >> TDC8PCI2_event_length;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }

#ifdef LINUX
		if ((TDC8PCI2_event_length & 0xff00000000000000LL) != 0xff00000000000000LL) {
#else
		if ((TDC8PCI2_event_length & 0xff00000000000000) != 0xff00000000000000) {
#endif
			this->errorflag = 2;
			return false;
		}

#ifdef LINUX
		TDC8PCI2_event_length = TDC8PCI2_event_length & 0x00ffffffffffffffLL;
#else
		TDC8PCI2_event_length = TDC8PCI2_event_length & 0x00ffffffffffffff;
#endif

		* input_lmf >> uint64_LMF_EventCounter;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
		}


	if (DAQ_ID == DAQ_ID_HM1 && DAQVersion >= 20080507) {
		unsigned __int64 event_length;
		*input_lmf >> event_length;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }

#ifdef LINUX
		if ((event_length & 0xff00000000000000LL) != 0xff00000000000000LL) {
			this->errorflag = 2;
			return false;
		}
		event_length = event_length & 0x00ffffffffffffffLL;
#else
		if ((event_length & 0xff00000000000000) != 0xff00000000000000) {
			this->errorflag = 2;
			return false;
		}
		event_length = event_length & 0x00ffffffffffffff;
#endif

		* input_lmf >> uint64_LMF_EventCounter;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
	}

	if (DAQ_ID == DAQ_ID_TDC4HM) {
		unsigned __int64 event_length;
		*input_lmf >> event_length;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }

#ifdef LINUX
		if ((event_length & 0xff00000000000000LL) != 0xff00000000000000LL) {
			this->errorflag = 2;
			return false;
		}
		event_length = event_length & 0x00ffffffffffffffLL;
#else
		if ((event_length & 0xff00000000000000) != 0xff00000000000000) {
			this->errorflag = 2;
			return false;
		}
		event_length = event_length & 0x00ffffffffffffff;
#endif

		* input_lmf >> uint64_LMF_EventCounter;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
	}

	++uint64_number_of_read_events;

	//-------------------------------
	//  Read Time Stamp

	if (timestamp_format > 0) {

		if (timestamp_format > 0) {
			myLARGE_INTEGER aaa;
			aaa.QuadPart = 0;
			*input_lmf >> aaa.LowPart;
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
			if (timestamp_format == 2) *input_lmf >> aaa.HighPart;
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 1; return false; }
			ui64_timestamp = aaa.QuadPart;
		}
		DOUBLE_timestamp = double(ui64_timestamp) / frequency;  // time stamp in seconds.
	}


	if (DAQ_ID != DAQ_ID_TDC4HM && DAQ_ID != DAQ_ID_SIMPLE && !TDC8HP.variable_event_length && !TDC8PCI2.variable_event_length && !TDC8HQ.variable_event_length) {
		for (i = 0; i < number_of_channels + number_of_channels2; ++i) {
			if (DAQ_ID == DAQ_ID_HM1_ABM) {
				number_of_hits[i] = 1;
				if (data_format_in_userheader == 2) *input_lmf >> us16TDC[i * num_ions];
				if (data_format_in_userheader == 5) *input_lmf >> dTDC[i * num_ions];
				if (data_format_in_userheader == 10) *input_lmf >> i32TDC[i * num_ions];
				if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			}
			if (DAQ_ID != DAQ_ID_HM1_ABM) {
				if (data_format_in_userheader == 2) {
					*input_lmf >> unsigned_short_Dummy;
					if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
					if (DAQ_ID == DAQ_ID_HM1) unsigned_short_Dummy = (unsigned_short_Dummy & 0x0007) - 1;
					number_of_hits[i] = (__int32)unsigned_short_Dummy;
					for (j = 0; j < max_number_of_hits; ++j)  *input_lmf >> us16TDC[i * num_ions + j];
				}
				if (data_format_in_userheader == 5) {
					*input_lmf >> double_Dummy;
					if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
					number_of_hits[i] = __int32(double_Dummy + 0.1);
					for (j = 0; j < max_number_of_hits; ++j)  *input_lmf >> dTDC[i * num_ions + j];
				}
				if (data_format_in_userheader == 10) {
					*input_lmf >> int_Dummy;
					if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
					number_of_hits[i] = (__int32)int_Dummy;
					for (j = 0; j < max_number_of_hits; ++j)  *input_lmf >> i32TDC[i * num_ions + j];
				}
				if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			}
		} // for i
	}

	if (DAQ_ID == DAQ_ID_HM1 && data_format_in_userheader == -1) {
		for (unsigned __int32 channel = 0; channel < number_of_channels + number_of_channels2; ++channel) {
			unsigned  __int16 nn;
			*input_lmf >> nn;		// store hits for this channel

			__int32 n = nn;
			n = (n & 0x07) - 1;		// now hits only
			n = n < 0 ? 0 : n;		// avoid "negative" hits
			if (n > __int32(max_number_of_hits)) n = max_number_of_hits;

			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			number_of_hits[channel] = n;
			for (__int32 i = 0; i < (__int32)n; ++i) {	// transfer selected hits
				unsigned __int16 us16data;
				*input_lmf >> us16data;
				us16TDC[channel * num_ions + i] = us16data;
			}

			if (DAQVersion > 20080507) {
				__int16 level_info;
				*input_lmf >> level_info;				// Data for LevelInfo compatibility
				*input_lmf >> number_of_bytes_in_PostEventData;
				if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
					input_lmf->error = 21;
					return false;
				}
				for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
					unsigned __int8 byte_dummy;
					*input_lmf >> byte_dummy;
					ui8_PostEventData[i] = byte_dummy;
				}
			}

			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
		}
	}

	if ((DAQ_ID == DAQ_ID_TDC8 || DAQ_ID == DAQ_ID_2TDC8) && TDC8PCI2.variable_event_length == 1) {
		for (unsigned __int32 channel = 0; channel < number_of_channels + number_of_channels2; ++channel) {
			unsigned  __int16 n;
			*input_lmf >> n;		// store hits for this channel

			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			number_of_hits[channel] = n;
			for (__int32 i = 0; i < (__int32)n; ++i) {	// transfer selected hits
				unsigned __int16 us16data;
				*input_lmf >> us16data;
				us16TDC[channel * num_ions + i] = us16data;
			}
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
		}
	}

	if (DAQ_ID == DAQ_ID_TDC4HM) {
		for (unsigned __int32 channel = 0; channel < number_of_channels; ++channel) {
			unsigned  __int16 n16;
			__int32 n;

			*input_lmf >> n16;		// store hits for this channel
			n = n16;

			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			number_of_hits[channel] = n;
			for (__int32 i = 0; i < (__int32)n; ++i) {	// transfer selected hits
				__int32 i32data;
				*input_lmf >> i32data;
				i32TDC[channel * num_ions + i] = i32data;
			}
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
		}

		*input_lmf >> ui64LevelInfo;

		changed_mask_read = 0;
		*input_lmf >> changed_mask_read;
		unsigned __int32 changed_mask = changed_mask_read;

		for (__int32 i = 0; i < 32; i++) {
			if (!changed_mask) break;
			if (changed_mask & 0x1) {
				double double_temp;
				*input_lmf >> double_temp;
				Parameter[901 + i] = double_temp;
			}
			changed_mask >>= 1;
		}

		number_of_bytes_in_PostEventData = 0;
		*input_lmf >> number_of_bytes_in_PostEventData;
		if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
			input_lmf->error = 21;
			return false;
		}
		for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
			unsigned __int8 byte_dummy;
			*input_lmf >> byte_dummy;
			ui8_PostEventData[i] = byte_dummy;
		}
	}

	if ((DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW) && TDC8HP.variable_event_length == 1) {
		for (unsigned __int32 channel = 0; channel < number_of_channels; ++channel) {
			unsigned  __int16 n16;
			unsigned  __int32 n32;
			__int32 n;
			if (TDC8HP.exotic_file_type) {
				*input_lmf >> n32;
				n = n32;
			}
			else {
				*input_lmf >> n16;		// store hits for this channel
				n = n16;
			}
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
			number_of_hits[channel] = n;
			for (__int32 i = 0; i < (__int32)n; ++i) {	// transfer selected hits
				__int32 i32data;
				*input_lmf >> i32data;
				i32TDC[channel * num_ions + i] = i32data;
			}
			if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
		}
		if (DAQ_ID == DAQ_ID_TDC8HP && this->LMF_Version >= 9) {
			*input_lmf >> ui64LevelInfo;
		}
		if (this->LMF_Version >= 11) {
			changed_mask_read = 0;
			*input_lmf >> changed_mask_read;
			unsigned __int32 changed_mask = changed_mask_read;
			if (changed_mask) {
				for (__int32 i = 0; i < 32; i++) {
					if (changed_mask & 0x1) {
						double double_temp;
						*input_lmf >> double_temp;
						Parameter[901 + i] = double_temp;
					}
					changed_mask >>= 1;
				}
			}
		}
		number_of_bytes_in_PostEventData = 0;
		if (DAQ_ID == DAQ_ID_TDC8HP && this->TDC8HP.UserHeaderVersion >= 7) {
			*input_lmf >> number_of_bytes_in_PostEventData;
			if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
				input_lmf->error = 21;
				return false;
			}
			for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
				unsigned __int8 byte_dummy;
				*input_lmf >> byte_dummy;
				ui8_PostEventData[i] = byte_dummy;
			}
		}
	}

	if (DAQ_ID == DAQ_ID_SIMPLE) {
		unsigned __int16 us16_Dummy;
		__int32 i32_Dummy;
		__int32 number_of_words;
		__int32 channel;
		number_of_words = 0;
		if (data_format_in_userheader == 2) { *input_lmf >> us16_Dummy; number_of_words = us16_Dummy; }
		if (data_format_in_userheader == 10) *input_lmf >> number_of_words;
		if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
		for (i = 0; i < number_of_channels; ++i) number_of_hits[i] = 0;

		bool read_channel_marker;
		read_channel_marker = true;
		if (data_format_in_userheader == 2) {
			while (number_of_words > 0) {
				number_of_words--;
				*input_lmf >> us16_Dummy;
				if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
				if (read_channel_marker) {
					read_channel_marker = false;
					channel = 0;
					channel = __int32((us16_Dummy & 0xff00) >> 8);
					number_of_hits[channel] = __int32(us16_Dummy & 0x00ff);
					i = 0;
				}
				else {
					us16TDC[channel * num_ions + i] = us16_Dummy;
					++i;
					if (i == number_of_hits[channel]) read_channel_marker = true;
				}
			}
		}
		if (data_format_in_userheader == 10) {
			while (number_of_words > 0) {
				number_of_words--;
				*input_lmf >> i32_Dummy;
				if (input_lmf->error) { if (input_lmf->eof) this->errorflag = 18; else this->errorflag = 2; return false; }
				if (read_channel_marker) {
					read_channel_marker = false;
					channel = 0;
					channel = __int32((i32_Dummy & 0xff000000) >> 24);
					number_of_hits[channel] = __int32(i32_Dummy & 0x000000ff);
					i = 0;
				}
				else {
					i32TDC[channel * num_ions + i] = i32_Dummy;
					++i;
					if (i == number_of_hits[channel]) read_channel_marker = true;
				}
			}
		}
	}

	if (LMF_Version >= 9 && DAQ_ID == DAQ_ID_2TDC8 && DAQVersion >= 20110208) {
		number_of_bytes_in_PostEventData = 0;
		*input_lmf >> number_of_bytes_in_PostEventData;
		if (number_of_bytes_in_PostEventData > MAX_NUMBER_OF_BYTES_IN_POSTEVENTDATA) {
			input_lmf->error = 21;
			return false;
		}
		for (__int32 i = 0; i < number_of_bytes_in_PostEventData; i++) {
			unsigned __int8 byte_dummy;
			*input_lmf >> byte_dummy;
			ui8_PostEventData[i] = byte_dummy;
		}
	}

	must_read_first = false;
	return true;
	}








/////////////////////////////////////////////////////////////////
void LMF_IO::WriteCAMACArray(double timestamp, unsigned __int32 data[])
/////////////////////////////////////////////////////////////////
{
	unsigned __int16 dummy_uint16;
	unsigned __int8  dummy_uint8;


	if (!output_lmf || !OutputFileIsOpen) {
		errorflag = 10;
		return;
	}

	++uint64_number_of_written_events;

	myLARGE_INTEGER LARGE_Timestamp;
	LARGE_Timestamp.QuadPart = (__int64)(timestamp * frequency);

	if (timestamp_format_output >= 1) {
		if (data_format_in_userheader_output == 2) {
			dummy_uint16 = (unsigned __int16)(LARGE_Timestamp.LowPart & 0x0000ffff); *output_lmf << dummy_uint16;			// 32 Bit Low part, lower  16 Bit
			dummy_uint16 = (unsigned __int16)(LARGE_Timestamp.LowPart & 0xffff0000); *output_lmf << dummy_uint16;			// 32 Bit Low part, higher 16 Bit
		}
		if (data_format_in_userheader_output == 6) {
			dummy_uint8 = (unsigned __int8)(LARGE_Timestamp.LowPart & 0x000000ff); *output_lmf << dummy_uint8;			// 32 Bit Low part, lower 16 Bit, lower 8 bit
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.LowPart >> 8) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit Low part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)0; *output_lmf << dummy_uint8;
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.LowPart >> 16) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit Low part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.LowPart >> 24) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit Low part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)0; *output_lmf << dummy_uint8;
		}
	}
	if (timestamp_format_output == 2) {
		if (data_format_in_userheader_output == 2) {
			dummy_uint16 = (unsigned __int16)(LARGE_Timestamp.HighPart & 0x0000ffff); *output_lmf << dummy_uint16;			// 32 Bit High part, lower  16 Bit
			dummy_uint16 = (unsigned __int16)(LARGE_Timestamp.HighPart & 0xffff0000); *output_lmf << dummy_uint16;			// 32 Bit High part, higher 16 Bit
		}
		if (data_format_in_userheader_output == 6) {
			dummy_uint8 = (unsigned __int8)(LARGE_Timestamp.HighPart & 0x000000ff); *output_lmf << dummy_uint8;			// 32 Bit High part, lower 16 Bit, lower 8 bit
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.HighPart >> 8) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit High part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)0; *output_lmf << dummy_uint8;
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.HighPart >> 16) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit High part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)((LARGE_Timestamp.HighPart >> 24) & 0x000000ff); *output_lmf << dummy_uint8;	// 32 Bit High part, lower 16 Bit, high 8 bit
			dummy_uint8 = (unsigned __int8)0; *output_lmf << dummy_uint8;
		}
	}

	__int32 i;

	for (i = 0; i < Numberofcoordinates - timestamp_format_output * 2; ++i) {
		if (data_format_in_userheader_output == 2) {
			dummy_uint16 = (unsigned __int16)(data[i] & 0x0000ffff); *output_lmf << dummy_uint16;
		}
		if (data_format_in_userheader_output == 6) {
			dummy_uint8 = (unsigned __int8)(data[i] & 0x000000ff); *output_lmf << dummy_uint8;
			dummy_uint8 = (unsigned __int8)((data[i] >> 8) & 0x000000ff); *output_lmf << dummy_uint8;
			dummy_uint8 = (unsigned __int8)((data[i] >> 16) & 0x000000ff); *output_lmf << dummy_uint8;
		}
	}

	return;
}






/////////////////////////////////////////////////////////////////
bool LMF_IO::ReadNextCAMACEvent()
/////////////////////////////////////////////////////////////////
{
	__int32 i;

	if (!input_lmf) {
		errorflag = 9;
		return false;
	}

	++uint64_number_of_read_events;

	//-------------------------------
	//  Read Time Stamp
	DOUBLE_timestamp = 0.;

	unsigned __int32 time_temp;
	unsigned __int8 byte_1, byte_2, byte_3;
	unsigned __int16 unsigned_short;

	if (timestamp_format > 0) {
		//TRY
		myLARGE_INTEGER LARGE_timestamp;
		LARGE_timestamp.QuadPart = 0;
		if (timestamp_format >= 1)
		{
			if (data_format_in_userheader == 2) {
				*input_lmf >> unsigned_short;
				time_temp = unsigned_short;
				*input_lmf >> unsigned_short;
				LARGE_timestamp.LowPart = time_temp + unsigned_short * 256 * 256;
			}
			if (data_format_in_userheader == 6) {
				*input_lmf >> byte_1; *input_lmf >> byte_2; *input_lmf >> byte_3;
				time_temp = byte_1 + byte_2 * 256 + byte_3 * 256 * 256;
				LARGE_timestamp.LowPart = time_temp;

				*input_lmf >> byte_1; *input_lmf >> byte_2; *input_lmf >> byte_3;
				time_temp = byte_1 + byte_2 * 256 + byte_3 * 256 * 256;
				LARGE_timestamp.LowPart += time_temp * 256 * 256;
			}
		}
		if (timestamp_format == 2) {
			if (data_format_in_userheader == 2) {
				*input_lmf >> unsigned_short;
				time_temp = unsigned_short;
				*input_lmf >> unsigned_short;
				LARGE_timestamp.HighPart = time_temp + unsigned_short * 256 * 256;
			}
			if (data_format_in_userheader == 6) {
				*input_lmf >> byte_1; *input_lmf >> byte_2; *input_lmf >> byte_3;
				time_temp = byte_1 + byte_2 * 256 + byte_3 * 256 * 256;
				LARGE_timestamp.HighPart = time_temp;

				*input_lmf >> byte_1; *input_lmf >> byte_2; *input_lmf >> byte_3;
				time_temp = byte_1 + byte_2 * 256 + byte_3 * 256 * 256;
				LARGE_timestamp.HighPart += time_temp * 256 * 256;
			}
		}
		ui64_timestamp = LARGE_timestamp.QuadPart;
		/*		CATCH(CArchiveException,e)
					errorflag = 1;	// error reading timestamp
					return false;
				END_CATCH
				*/
		DOUBLE_timestamp = double(ui64_timestamp) / frequency;  // time stamp in seconds.
	}

	//	TRY
	for (i = 0; i < Numberofcoordinates - timestamp_format * 2; ++i) {
		if (data_format_in_userheader == 6) {
			*input_lmf >> byte_1; *input_lmf >> byte_2; *input_lmf >> byte_3;
			CAMAC_Data[i] = byte_1 + byte_2 * 256 + byte_3 * 256 * 256;
		}
		if (data_format_in_userheader == 2) {
			*input_lmf >> unsigned_short;
			CAMAC_Data[i] = unsigned_short;
		}
	} // for i
/*	CATCH(CArchiveException,e)
		errorflag = 2; // error reading data
		return false;
	END_CATCH
	*/

	must_read_first = false;
	return true;
}





/////////////////////////////////////////////
void LMF_IO::GetCAMACArray(unsigned __int32 data[])
/////////////////////////////////////////////
{
	if (must_read_first) {
		if (!ReadNextCAMACEvent()) return;
	}
	for (__int32 i = 0; i < Numberofcoordinates - timestamp_format * 2; ++i) data[i] = CAMAC_Data[i];
}





/////////////////////////////////////////////////////////////////
void LMF_IO::GetTDCDataArray(__int32* tdc, __int32 max_channel, __int32 max_hits)
/////////////////////////////////////////////////////////////////
{
	__int32 i, j;
	__int32 ii;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	if (data_format_in_userheader == LM_USERDEF) {
		if (DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW || DAQ_ID == DAQ_ID_TDC4HM) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = i32TDC[i * num_ions + j];
			}
		}
		if (DAQ_ID == DAQ_ID_TDC8 || DAQ_ID == DAQ_ID_2TDC8 || DAQ_ID == DAQ_ID_HM1) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = us16TDC[i * num_ions + j];
			}
		}
	}
	if (data_format_in_userheader == 10) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = i32TDC[i * num_ions + j];
		}
	}
	if (data_format_in_userheader == 2) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = __int32(us16TDC[i * num_ions + j]);
		}
	}
	if (data_format_in_userheader == 5) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) {
				if (dTDC[i * num_ions + j] >= 0.) ii = __int32(dTDC[i * num_ions + j] + 1.e-19);
				if (dTDC[i * num_ions + j] < 0.) ii = __int32(dTDC[i * num_ions + j] - 1.e-19);
				tdc[i * num_ions + j] = ii;
			}
		}
	}
}



/////////////////////////////////////////////////////////////////
void LMF_IO::GetTDCDataArray(__int32* tdc)
/////////////////////////////////////////////////////////////////
{
	GetTDCDataArray(tdc, num_channels, num_ions);
}


/////////////////////////////////////////////////////////////////
void LMF_IO::GetTDCDataArray(__int64* tdc)
/////////////////////////////////////////////////////////////////
{
	__int32 i, j;
	__int32 ii;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	//__int32 max_channel = (number_of_channels+number_of_channels2 < num_channels) ? (number_of_channels+number_of_channels2) : num_channels;
	//__int32 max_hits = (max_number_of_hits < num_ions) ? max_number_of_hits : num_ions;
	__int32 max_channel = num_channels;
	__int32 max_hits = num_ions;

	if (DAQ_ID == DAQ_ID_TDC8HQ) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = i64TDC[i * num_ions + j];
		}
		return;
	}

	if (data_format_in_userheader == LM_USERDEF) {
		if (DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = i32TDC[i * num_ions + j];
			}
		}
		if (DAQ_ID == DAQ_ID_TDC8 || DAQ_ID == DAQ_ID_2TDC8 || DAQ_ID == DAQ_ID_HM1) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = us16TDC[i * num_ions + j];
			}
		}
	}
	if (data_format_in_userheader == 10) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = i32TDC[i * num_ions + j];
		}
	}
	if (data_format_in_userheader == 2) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = __int32(us16TDC[i * num_ions + j]);
		}
	}
	if (data_format_in_userheader == 5) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) {
				if (dTDC[i * num_ions + j] >= 0.) ii = __int32(dTDC[i * num_ions + j] + 1.e-19);
				if (dTDC[i * num_ions + j] < 0.) ii = __int32(dTDC[i * num_ions + j] - 1.e-19);
				tdc[i * num_ions + j] = ii;
			}
		}
	}
}




/////////////////////////////////////////////////////////////////
void LMF_IO::GetTDCDataArray(unsigned __int16* tdc)
/////////////////////////////////////////////////////////////////
{
	__int32 i, j;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	//__int32 max_channel = (number_of_channels+number_of_channels2 < num_channels) ? (number_of_channels+number_of_channels2) : num_channels;
	//__int32 max_hits = (max_number_of_hits < num_ions) ? max_number_of_hits : num_ions;
	__int32 max_channel = num_channels;
	__int32 max_hits = num_ions;

	if (data_format_in_userheader == LM_USERDEF) {
		if (DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = (unsigned __int16)(i32TDC[i * num_ions + j]);
			}
		}
		if (DAQ_ID == DAQ_ID_TDC8 || DAQ_ID == DAQ_ID_2TDC8 || DAQ_ID == DAQ_ID_HM1) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = (unsigned __int16)(us16TDC[i * num_ions + j]);
			}
		}
	}
	if (data_format_in_userheader == 10) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = (unsigned __int16)(i32TDC[i * num_ions + j]);
		}
	}
	if (data_format_in_userheader == 2) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = us16TDC[i * num_ions + j];
		}
	}
	if (data_format_in_userheader == 5) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = (unsigned __int16)(dTDC[i * num_ions + j] + 1e-7);
		}
	}
}



/////////////////////////////////////////////////////////////////
void LMF_IO::GetTDCDataArray(double* tdc)
/////////////////////////////////////////////////////////////////
{
	__int32 i, j;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	//__int32 max_channel = (number_of_channels+number_of_channels2 < num_channels) ? (number_of_channels+number_of_channels2) : num_channels;
	//__int32 max_hits = (max_number_of_hits < num_ions) ? max_number_of_hits : num_ions;
	__int32 max_channel = num_channels;
	__int32 max_hits = num_ions;

	if (data_format_in_userheader == LM_USERDEF) {
		if (DAQ_ID == DAQ_ID_TDC8HP || DAQ_ID == DAQ_ID_TDC8HPRAW) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = double(i32TDC[i * num_ions + j]);
			}
		}
		if (DAQ_ID == DAQ_ID_TDC8 || DAQ_ID == DAQ_ID_2TDC8 || DAQ_ID == DAQ_ID_HM1) {
			for (i = 0; i < max_channel; ++i) {
				for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = double(us16TDC[i * num_ions + j]);
			}
		}
	}
	if (data_format_in_userheader == 10) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = double(i32TDC[i * num_ions + j]);
		}
	}
	if (data_format_in_userheader == 2) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = double(us16TDC[i * num_ions + j]);
		}
	}
	if (data_format_in_userheader == 5) {
		for (i = 0; i < max_channel; ++i) {
			for (j = 0; j < max_hits; ++j) tdc[i * num_ions + j] = dTDC[i * num_ions + j] + 1e-7;
		}
	}
}





/////////////////////////////////////////////////////////////////
void LMF_IO::GetNumberOfHitsArray(unsigned __int32 cnt[]) {
	/////////////////////////////////////////////////////////////////
	__int32 i;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	for (i = 0; i < num_channels; ++i) cnt[i] = (number_of_hits[i] < (unsigned __int32)(num_ions)) ? number_of_hits[i] : num_ions;
}




/////////////////////////////////////////////////////////////////
void LMF_IO::GetNumberOfHitsArray(__int32 cnt[]) {
	/////////////////////////////////////////////////////////////////
	__int32 i;

	if (must_read_first) {
		if (!ReadNextEvent()) return;
	}

	for (i = 0; i < num_channels; ++i) cnt[i] = (number_of_hits[i] < (unsigned __int32)(num_ions)) ? number_of_hits[i] : num_ions;
}




/////////////////////////////////////////////////////////////////
const char* LMF_IO::GetErrorText(__int32 error_id)
/////////////////////////////////////////////////////////////////
{
	return error_text[error_id];
}


/////////////////////////////////////////////////////////////////
void LMF_IO::GetErrorText(__int32 error_code, __int8 text[])
/////////////////////////////////////////////////////////////////
{
	sprintf(text, "%s", error_text[error_code]);
	return;
}


/////////////////////////////////////////////////////////////////
void LMF_IO::GetErrorText(__int8 text[])
/////////////////////////////////////////////////////////////////
{
	GetErrorText(errorflag, text);
	return;
}


/////////////////////////////////////////////////////////////////
unsigned __int64 LMF_IO::GetEventNumber()
/////////////////////////////////////////////////////////////////
{
	return uint64_number_of_read_events;
}

/////////////////////////////////////////////////////////////////
unsigned __int32 LMF_IO::GetNumberOfChannels()
/////////////////////////////////////////////////////////////////
{
	return number_of_channels + number_of_channels2;
}

/////////////////////////////////////////////////////////////////
unsigned __int32 LMF_IO::GetMaxNumberOfHits()
/////////////////////////////////////////////////////////////////
{
	return max_number_of_hits;
}


/////////////////////////////////////////////////////////////////
double LMF_IO::GetDoubleTimeStamp()
/////////////////////////////////////////////////////////////////
{
	if (must_read_first) {
		if ((DAQ_ID != DAQ_ID_FADC4) && (DAQ_ID != DAQ_ID_FADC8)) {
			if (!ReadNextEvent()) return 0.;
		}
	}
	return DOUBLE_timestamp;
}

/////////////////////////////////////////////////////////////////
unsigned __int64 LMF_IO::Getuint64TimeStamp()
/////////////////////////////////////////////////////////////////
{
	if (must_read_first) {
		if (!ReadNextEvent()) return ui64_timestamp;
	}
	return ui64_timestamp;
}




/////////////////////////////////////////////////////////////////
bool LMF_IO::Clone(LMF_IO * clone)
/////////////////////////////////////////////////////////////////
{
	if (!clone) return 0;

	clone->Versionstring = this->Versionstring;
	clone->FilePathName = this->FilePathName;
	clone->OutputFilePathName = this->OutputFilePathName;
	clone->Comment = this->Comment;
	clone->Comment_output = this->Comment_output;
	clone->DAQ_info = this->DAQ_info;
	clone->Camac_CIF = this->Camac_CIF;

	clone->iLMFcompression = this->iLMFcompression;

	clone->Starttime = this->Starttime;
	clone->Stoptime = this->Stoptime;
	clone->Starttime_output = this->Starttime_output;
	clone->Stoptime_output = this->Stoptime_output;

	clone->time_reference = this->time_reference;
	clone->time_reference_output = this->time_reference_output;

	clone->ArchiveFlag = this->ArchiveFlag;
	clone->Cobold_Header_version = this->Cobold_Header_version;
	clone->Cobold_Header_version_output = this->Cobold_Header_version_output;

	clone->uint64_LMF_EventCounter = this->uint64_LMF_EventCounter;
	clone->uint64_number_of_read_events = this->uint64_number_of_read_events;
	clone->uint64_Numberofevents = this->uint64_Numberofevents;

	clone->Numberofcoordinates = this->Numberofcoordinates;
	clone->CTime_version = this->CTime_version;
	clone->CTime_version_output = this->CTime_version_output;
	clone->CTime_version_output = this->CTime_version_output;
	clone->SIMPLE_DAQ_ID_Orignial = this->SIMPLE_DAQ_ID_Orignial;
	clone->DAQVersion = this->DAQVersion;
	clone->DAQVersion_output = this->DAQVersion_output;
	clone->DAQ_ID = this->DAQ_ID;
	clone->DAQ_ID_output = this->DAQ_ID_output;
	clone->data_format_in_userheader = this->data_format_in_userheader;
	clone->data_format_in_userheader_output = this->data_format_in_userheader_output;

	clone->Headersize = this->Headersize;
	clone->User_header_size = this->User_header_size;
	clone->User_header_size_output = this->User_header_size_output;

	clone->IOaddress = this->IOaddress;
	clone->timestamp_format = this->timestamp_format;
	clone->timestamp_format_output = this->timestamp_format_output;
	clone->timerange = this->timerange;

	clone->number_of_channels = this->number_of_channels;
	clone->number_of_channels2 = this->number_of_channels2;
	clone->max_number_of_hits = this->max_number_of_hits;
	clone->max_number_of_hits2 = this->max_number_of_hits2;

	clone->number_of_channels_output = this->number_of_channels_output;
	clone->number_of_channels2_output = this->number_of_channels2_output;
	clone->max_number_of_hits_output = this->max_number_of_hits_output;
	clone->max_number_of_hits2_output = this->max_number_of_hits2_output;

	clone->DAQSubVersion = this->DAQSubVersion;
	clone->module_2nd = this->module_2nd;
	clone->system_timeout = this->system_timeout;
	clone->system_timeout_output = this->system_timeout_output;
	clone->common_mode = this->common_mode;
	clone->common_mode_output = this->common_mode_output;
	clone->DAQ_info_Length = this->DAQ_info_Length;
	clone->Camac_CIF_Length = this->Camac_CIF_Length;
	clone->LMF_Version = this->LMF_Version;
	clone->LMF_Version_output = this->LMF_Version_output;
	clone->TDCDataType = this->TDCDataType;

	clone->LMF_Header_version = this->LMF_Header_version;

	clone->number_of_bytes_in_PostEventData = this->number_of_bytes_in_PostEventData;

	clone->tdcresolution = this->tdcresolution;
	clone->tdcresolution_output = this->tdcresolution_output;
	clone->frequency = this->frequency;
	clone->DOUBLE_timestamp = this->DOUBLE_timestamp;
	clone->ui64_timestamp = this->ui64_timestamp;

	clone->number_of_CCFHistory_strings = this->number_of_CCFHistory_strings;
	clone->number_of_DAN_source_strings = this->number_of_DAN_source_strings;
	clone->number_of_DAQ_source_strings = this->number_of_DAQ_source_strings;
	clone->number_of_CCFHistory_strings_output = this->number_of_CCFHistory_strings_output;
	clone->number_of_DAN_source_strings_output = this->number_of_DAN_source_strings_output;
	clone->number_of_DAQ_source_strings_output = this->number_of_DAQ_source_strings_output;

	if (number_of_CCFHistory_strings >= 0) {
		clone->CCFHistory_strings = new std::string * [number_of_CCFHistory_strings];
		memset(clone->CCFHistory_strings, 0, sizeof(std::string*) * number_of_CCFHistory_strings);
	}
	if (number_of_DAN_source_strings >= 0) {
		clone->DAN_source_strings = new std::string * [number_of_DAN_source_strings];
		memset(clone->DAN_source_strings, 0, sizeof(std::string*) * number_of_DAN_source_strings);
	}
	if (number_of_DAQ_source_strings >= 0) {
		clone->DAQ_source_strings = new std::string * [number_of_DAQ_source_strings];
		memset(clone->DAQ_source_strings, 0, sizeof(std::string*) * number_of_DAQ_source_strings);
	}
	if (this->CCFHistory_strings) {
		for (__int32 i = 0; i < number_of_CCFHistory_strings; ++i) { clone->CCFHistory_strings[i] = new std::string(); *clone->CCFHistory_strings[i] = *this->CCFHistory_strings[i]; }
	}
	if (this->DAN_source_strings) {
		for (__int32 i = 0; i < number_of_DAN_source_strings; ++i) { clone->DAN_source_strings[i] = new std::string(); *clone->DAN_source_strings[i] = *this->DAN_source_strings[i]; }
	}
	if (this->DAQ_source_strings) {
		for (__int32 i = 0; i < number_of_DAQ_source_strings; ++i) { clone->DAQ_source_strings[i] = new std::string(); *clone->DAQ_source_strings[i] = *this->DAQ_source_strings[i]; }
	}

	if (number_of_CCFHistory_strings_output >= 0) {
		clone->CCFHistory_strings_output = new std::string * [number_of_CCFHistory_strings_output];
		memset(clone->CCFHistory_strings_output, 0, sizeof(std::string*) * number_of_CCFHistory_strings_output);
	}
	if (number_of_DAN_source_strings_output >= 0) {
		clone->DAN_source_strings_output = new std::string * [number_of_DAN_source_strings_output];
		memset(clone->DAN_source_strings_output, 0, sizeof(std::string*) * number_of_DAN_source_strings_output);
	}
	if (number_of_DAQ_source_strings_output >= 0) {
		clone->DAQ_source_strings_output = new std::string * [number_of_DAQ_source_strings_output];
		memset(clone->DAQ_source_strings_output, 0, sizeof(std::string*) * number_of_DAQ_source_strings_output);
	}
	if (this->CCFHistory_strings_output) {
		for (__int32 i = 0; i < number_of_CCFHistory_strings_output; ++i) { clone->CCFHistory_strings_output[i] = new std::string(); *clone->CCFHistory_strings_output[i] = *this->CCFHistory_strings_output[i]; }
	}
	if (this->DAN_source_strings_output) {
		for (__int32 i = 0; i < number_of_DAN_source_strings_output; ++i) { clone->DAN_source_strings_output[i] = new std::string(); *clone->DAN_source_strings_output[i] = *this->DAN_source_strings_output[i]; }
	}
	if (this->DAQ_source_strings_output) {
		for (__int32 i = 0; i < number_of_DAQ_source_strings_output; ++i) { clone->DAQ_source_strings_output[i] = new std::string(); *clone->DAQ_source_strings_output[i] = *this->DAQ_source_strings_output[i]; }
	}

	clone->CCF_HISTORY_CODE_bitmasked = this->CCF_HISTORY_CODE_bitmasked;
	clone->DAN_SOURCE_CODE_bitmasked = this->DAN_SOURCE_CODE_bitmasked;
	clone->DAQ_SOURCE_CODE_bitmasked = this->DAQ_SOURCE_CODE_bitmasked;

	clone->errorflag = this->errorflag;
	clone->skip_header = this->skip_header;

	clone->uint64_number_of_written_events = this->uint64_number_of_written_events;

	clone->not_Cobold_LMF = this->not_Cobold_LMF;
	clone->Headersize_output = this->Headersize_output;
	clone->output_byte_counter = this->output_byte_counter;
	clone->Numberofcoordinates_output = this->Numberofcoordinates_output;
	clone->must_read_first = this->must_read_first;

	clone->num_channels = this->num_channels;
	clone->num_ions = this->num_ions;



	// pointers and other special stuff:


	//clone->InputFileIsOpen		= this->InputFileIsOpen;
	//clone->in_ar					= this->in_ar;
	//clone->input_lmf				= this->input_lmf;

	//clone->OutputFileIsOpen			= this->OutputFileIsOpen;
	//clone->out_ar					= this->out_ar;
	//clone->output_lmf				= this->output_lmf;


		// TDC8PCI2
	clone->TDC8PCI2.GateDelay_1st_card = this->TDC8PCI2.GateDelay_1st_card;
	clone->TDC8PCI2.OpenTime_1st_card = this->TDC8PCI2.OpenTime_1st_card;
	clone->TDC8PCI2.WriteEmptyEvents_1st_card = this->TDC8PCI2.WriteEmptyEvents_1st_card;
	clone->TDC8PCI2.TriggerFalling_1st_card = this->TDC8PCI2.TriggerFalling_1st_card;
	clone->TDC8PCI2.TriggerRising_1st_card = this->TDC8PCI2.TriggerRising_1st_card;
	clone->TDC8PCI2.EmptyCounter_1st_card = this->TDC8PCI2.EmptyCounter_1st_card;
	clone->TDC8PCI2.EmptyCounter_since_last_Event_1st_card = this->TDC8PCI2.EmptyCounter_since_last_Event_1st_card;
	clone->TDC8PCI2.use_normal_method = this->TDC8PCI2.use_normal_method;
	clone->TDC8PCI2.use_normal_method_2nd_card = this->TDC8PCI2.use_normal_method_2nd_card;
	clone->TDC8PCI2.sync_test_on_off = this->TDC8PCI2.sync_test_on_off;
	clone->TDC8PCI2.io_address_2nd_card = this->TDC8PCI2.io_address_2nd_card;
	clone->TDC8PCI2.GateDelay_2nd_card = this->TDC8PCI2.GateDelay_2nd_card;
	clone->TDC8PCI2.OpenTime_2nd_card = this->TDC8PCI2.OpenTime_2nd_card;
	clone->TDC8PCI2.WriteEmptyEvents_2nd_card = this->TDC8PCI2.WriteEmptyEvents_2nd_card;
	clone->TDC8PCI2.TriggerFallingEdge_2nd_card = this->TDC8PCI2.TriggerFallingEdge_2nd_card;
	clone->TDC8PCI2.TriggerRisingEdge_2nd_card = this->TDC8PCI2.TriggerRisingEdge_2nd_card;
	clone->TDC8PCI2.EmptyCounter_2nd_card = this->TDC8PCI2.EmptyCounter_2nd_card;
	clone->TDC8PCI2.EmptyCounter_since_last_Event_2nd_card = this->TDC8PCI2.EmptyCounter_since_last_Event_2nd_card;
	clone->TDC8PCI2.variable_event_length = this->TDC8PCI2.variable_event_length;
	clone->TDC8PCI2.i32NumberOfDAQLoops = this->TDC8PCI2.i32NumberOfDAQLoops;

	// HM1
	clone->HM1.FAK_DLL_Value = this->HM1.FAK_DLL_Value;
	clone->HM1.Resolution_Flag = this->HM1.Resolution_Flag;
	clone->HM1.trigger_mode_for_start = this->HM1.trigger_mode_for_start;
	clone->HM1.trigger_mode_for_stop = this->HM1.trigger_mode_for_stop;
	clone->HM1.Even_open_time = this->HM1.Even_open_time;
	clone->HM1.Auto_Trigger = this->HM1.Auto_Trigger;
	clone->HM1.set_bits_for_GP1 = this->HM1.set_bits_for_GP1;
	clone->HM1.ABM_m_xFrom = this->HM1.ABM_m_xFrom;
	clone->HM1.ABM_m_xTo = this->HM1.ABM_m_xTo;
	clone->HM1.ABM_m_yFrom = this->HM1.ABM_m_yFrom;
	clone->HM1.ABM_m_yTo = this->HM1.ABM_m_yTo;
	clone->HM1.ABM_m_xMin = this->HM1.ABM_m_xMin;
	clone->HM1.ABM_m_xMax = this->HM1.ABM_m_xMax;
	clone->HM1.ABM_m_yMin = this->HM1.ABM_m_yMin;
	clone->HM1.ABM_m_yMax = this->HM1.ABM_m_yMax;
	clone->HM1.ABM_m_xOffset = this->HM1.ABM_m_xOffset;
	clone->HM1.ABM_m_yOffset = this->HM1.ABM_m_yOffset;
	clone->HM1.ABM_m_zOffset = this->HM1.ABM_m_zOffset;
	clone->HM1.ABM_Mode = this->HM1.ABM_Mode;
	clone->HM1.ABM_OsziDarkInvert = this->HM1.ABM_OsziDarkInvert;
	clone->HM1.ABM_ErrorHisto = this->HM1.ABM_ErrorHisto;
	clone->HM1.ABM_XShift = this->HM1.ABM_XShift;
	clone->HM1.ABM_YShift = this->HM1.ABM_YShift;
	clone->HM1.ABM_ZShift = this->HM1.ABM_ZShift;
	clone->HM1.ABM_ozShift = this->HM1.ABM_ozShift;
	clone->HM1.ABM_wdShift = this->HM1.ABM_wdShift;
	clone->HM1.ABM_ucLevelXY = this->HM1.ABM_ucLevelXY;
	clone->HM1.ABM_ucLevelZ = this->HM1.ABM_ucLevelZ;
	clone->HM1.ABM_uiABMXShift = this->HM1.ABM_uiABMXShift;
	clone->HM1.ABM_uiABMYShift = this->HM1.ABM_uiABMYShift;
	clone->HM1.ABM_uiABMZShift = this->HM1.ABM_uiABMZShift;
	clone->HM1.use_normal_method = this->HM1.use_normal_method;

	clone->HM1.TWOHM1_FAK_DLL_Value = this->HM1.TWOHM1_FAK_DLL_Value;
	clone->HM1.TWOHM1_Resolution_Flag = this->HM1.TWOHM1_Resolution_Flag;
	clone->HM1.TWOHM1_trigger_mode_for_start = this->HM1.TWOHM1_trigger_mode_for_start;
	clone->HM1.TWOHM1_trigger_mode_for_stop = this->HM1.TWOHM1_trigger_mode_for_stop;
	clone->HM1.TWOHM1_res_adjust = this->HM1.TWOHM1_res_adjust;
	clone->HM1.TWOHM1_tdcresolution = this->HM1.TWOHM1_tdcresolution;
	clone->HM1.TWOHM1_test_overflow = this->HM1.TWOHM1_test_overflow;
	clone->HM1.TWOHM1_number_of_channels = this->HM1.TWOHM1_number_of_channels;
	clone->HM1.TWOHM1_number_of_hits = this->HM1.TWOHM1_number_of_hits;
	clone->HM1.TWOHM1_set_bits_for_GP1 = this->HM1.TWOHM1_set_bits_for_GP1;
	clone->HM1.TWOHM1_HM1_ID_1 = this->HM1.TWOHM1_HM1_ID_1;
	clone->HM1.TWOHM1_HM1_ID_2 = this->HM1.TWOHM1_HM1_ID_2;

	clone->TDC8HP.no_config_file_read = this->TDC8HP.no_config_file_read;
	clone->TDC8HP.RisingEnable_p61 = this->TDC8HP.RisingEnable_p61;
	clone->TDC8HP.FallingEnable_p62 = this->TDC8HP.FallingEnable_p62;
	clone->TDC8HP.TriggerEdge_p63 = this->TDC8HP.TriggerEdge_p63;
	clone->TDC8HP.TriggerChannel_p64 = this->TDC8HP.TriggerChannel_p64;
	clone->TDC8HP.OutputLevel_p65 = this->TDC8HP.OutputLevel_p65;
	clone->TDC8HP.GroupingEnable_p66 = this->TDC8HP.GroupingEnable_p66;
	clone->TDC8HP.GroupingEnable_p66_output = this->TDC8HP.GroupingEnable_p66_output;
	clone->TDC8HP.AllowOverlap_p67 = this->TDC8HP.AllowOverlap_p67;
	clone->TDC8HP.TriggerDeadTime_p68 = this->TDC8HP.TriggerDeadTime_p68;
	clone->TDC8HP.GroupRangeStart_p69 = this->TDC8HP.GroupRangeStart_p69;
	clone->TDC8HP.GroupRangeEnd_p70 = this->TDC8HP.GroupRangeEnd_p70;
	clone->TDC8HP.ExternalClock_p71 = this->TDC8HP.ExternalClock_p71;
	clone->TDC8HP.OutputRollOvers_p72 = this->TDC8HP.OutputRollOvers_p72;
	clone->TDC8HP.DelayTap0_p73 = this->TDC8HP.DelayTap0_p73;
	clone->TDC8HP.DelayTap1_p74 = this->TDC8HP.DelayTap1_p74;
	clone->TDC8HP.DelayTap2_p75 = this->TDC8HP.DelayTap2_p75;
	clone->TDC8HP.DelayTap3_p76 = this->TDC8HP.DelayTap3_p76;
	clone->TDC8HP.INL_p80 = this->TDC8HP.INL_p80;
	clone->TDC8HP.DNL_p81 = this->TDC8HP.DNL_p81;
	clone->TDC8HP.csConfigFile = this->TDC8HP.csConfigFile;
	clone->TDC8HP.csINLFile = this->TDC8HP.csINLFile;
	clone->TDC8HP.csDNLFile = this->TDC8HP.csDNLFile;
	clone->TDC8HP.csConfigFile_Length = this->TDC8HP.csConfigFile_Length;
	clone->TDC8HP.csINLFile_Length = this->TDC8HP.csINLFile_Length;
	clone->TDC8HP.csDNLFile_Length = this->TDC8HP.csDNLFile_Length;
	clone->TDC8HP.UserHeaderVersion = this->TDC8HP.UserHeaderVersion;
	clone->TDC8HP.VHR_25ps = this->TDC8HP.VHR_25ps;
	clone->TDC8HP.SyncValidationChannel = this->TDC8HP.SyncValidationChannel;
	clone->TDC8HP.variable_event_length = this->TDC8HP.variable_event_length;
	clone->TDC8HP.SSEEnable = this->TDC8HP.SSEEnable;
	clone->TDC8HP.MMXEnable = this->TDC8HP.MMXEnable;
	clone->TDC8HP.DMAEnable = this->TDC8HP.DMAEnable;
	clone->TDC8HP.GroupTimeOut = this->TDC8HP.GroupTimeOut;

	clone->TDC8HP.i32NumberOfDAQLoops = this->TDC8HP.i32NumberOfDAQLoops;
	clone->TDC8HP.TDC8HP_DriverVersion = this->TDC8HP.TDC8HP_DriverVersion;
	clone->TDC8HP.iTriggerChannelMask = this->TDC8HP.iTriggerChannelMask;
	clone->TDC8HP.iTime_zero_channel = this->TDC8HP.iTime_zero_channel;

	clone->TDC8HP.Number_of_TDCs = this->TDC8HP.Number_of_TDCs;
	for (__int32 i = 0; i < 3; ++i) {
		if (this->TDC8HP.TDC_info[i]) {
			clone->TDC8HP.TDC_info[i]->index = this->TDC8HP.TDC_info[i]->index;
			clone->TDC8HP.TDC_info[i]->channelCount = this->TDC8HP.TDC_info[i]->channelCount;
			clone->TDC8HP.TDC_info[i]->channelStart = this->TDC8HP.TDC_info[i]->channelStart;
			clone->TDC8HP.TDC_info[i]->highResChannelCount = this->TDC8HP.TDC_info[i]->highResChannelCount;
			clone->TDC8HP.TDC_info[i]->highResChannelStart = this->TDC8HP.TDC_info[i]->highResChannelStart;
			clone->TDC8HP.TDC_info[i]->lowResChannelCount = this->TDC8HP.TDC_info[i]->lowResChannelCount;
			clone->TDC8HP.TDC_info[i]->lowResChannelStart = this->TDC8HP.TDC_info[i]->lowResChannelStart;
			clone->TDC8HP.TDC_info[i]->resolution = this->TDC8HP.TDC_info[i]->resolution;
			clone->TDC8HP.TDC_info[i]->serialNumber = this->TDC8HP.TDC_info[i]->serialNumber;
			clone->TDC8HP.TDC_info[i]->version = this->TDC8HP.TDC_info[i]->version;
			clone->TDC8HP.TDC_info[i]->fifoSize = this->TDC8HP.TDC_info[i]->fifoSize;
			clone->TDC8HP.TDC_info[i]->flashValid = this->TDC8HP.TDC_info[i]->flashValid;
			memcpy(clone->TDC8HP.TDC_info[i]->INLCorrection, this->TDC8HP.TDC_info[i]->INLCorrection, sizeof(__int32) * 8 * 1024);
			memcpy(clone->TDC8HP.TDC_info[i]->DNLData, this->TDC8HP.TDC_info[i]->DNLData, sizeof(__int16) * 8 * 1024);
		}
	}

	clone->TDC8HP.veto_start = this->TDC8HP.veto_start;
	clone->TDC8HP.veto_end = this->TDC8HP.veto_end;
	clone->TDC8HP.filter_mask_1 = this->TDC8HP.filter_mask_1;
	clone->TDC8HP.filter_mask_2 = this->TDC8HP.filter_mask_2;
	clone->TDC8HP.i32AdvancedTriggerChannel = this->TDC8HP.i32AdvancedTriggerChannel;
	clone->TDC8HP.i32AdvancedTriggerChannel_start = this->TDC8HP.i32AdvancedTriggerChannel_start;
	clone->TDC8HP.i32AdvancedTriggerChannel_stop = this->TDC8HP.i32AdvancedTriggerChannel_stop;
	clone->TDC8HP.Time_zero_channel_offset_s = this->TDC8HP.Time_zero_channel_offset_s;
	clone->TDC8HP.veto_exclusion_mask = this->TDC8HP.veto_exclusion_mask;


	clone->fADC8.driver_version = this->fADC8.driver_version;
	clone->fADC8.i32NumberOfDAQLoops = this->fADC8.i32NumberOfDAQLoops;
	clone->fADC8.number_of_bools = this->fADC8.number_of_bools;
	clone->fADC8.number_of_int32s = this->fADC8.number_of_int32s;
	clone->fADC8.number_of_uint32s = this->fADC8.number_of_uint32s;
	clone->fADC8.number_of_doubles = this->fADC8.number_of_doubles;
	clone->fADC8.GroupEndMarker = this->fADC8.GroupEndMarker;
	clone->fADC8.i32NumberOfADCmodules = this->fADC8.i32NumberOfADCmodules;
	clone->fADC8.iEnableGroupMode = this->fADC8.iEnableGroupMode;
	clone->fADC8.iTriggerChannel = this->fADC8.iTriggerChannel;
	clone->fADC8.iPreSamplings_in_4800ps_units = this->fADC8.iPreSamplings_in_4800ps_units;
	clone->fADC8.iPostSamplings_in_9600ps_units = this->fADC8.iPostSamplings_in_9600ps_units;
	clone->fADC8.iEnableTDCinputs = this->fADC8.iEnableTDCinputs;
	clone->fADC8.bReadCustomData = this->fADC8.bReadCustomData;
	clone->fADC8.veto_gate_length = this->fADC8.veto_gate_length;
	clone->fADC8.veto_delay_length = this->fADC8.veto_delay_length;
	clone->fADC8.veto_mask = this->fADC8.veto_mask;
	clone->fADC8.dGroupRangeStart = this->fADC8.dGroupRangeStart;
	clone->fADC8.dGroupRangeEnd = this->fADC8.dGroupRangeEnd;
	clone->fADC8.at_least_1_signal_was_written = this->fADC8.at_least_1_signal_was_written;
	for (__int32 m = 0; m < 8; m++) {
		clone->fADC8.firmware_version[m] = this->fADC8.firmware_version[m];
		clone->fADC8.serial_number[m] = this->fADC8.serial_number[m];
		for (__int32 adc = 0; adc < 2; adc++) {
			clone->fADC8.dSyncTimeOffset[m][adc] = this->fADC8.dSyncTimeOffset[m][adc];
			clone->fADC8.iChannelMode[m][adc] = this->fADC8.iChannelMode[m][adc];								 // 0 = 1.25Gs, 1 = 2.5Gs, 2 = 5Gs
			clone->fADC8.iThreshold_GT[m][m] = this->fADC8.iThreshold_GT[m][m];
			clone->fADC8.iThreshold_LT[m][m] = this->fADC8.iThreshold_LT[m][m];
			clone->fADC8.iSynchronMode[m][adc] = this->fADC8.iSynchronMode[m][adc];
		}
		for (__int32 ch = 0; ch < 10; ch++) clone->fADC8.GND_level[m][ch] = this->fADC8.GND_level[m][ch];
	}


	clone->fADC4.packet_count = this->fADC4.packet_count;
	clone->fADC4.number_of_bools = this->fADC4.number_of_bools;
	clone->fADC4.number_of_int32s = this->fADC4.number_of_int32s;
	clone->fADC4.number_of_uint32s = this->fADC4.number_of_uint32s;
	clone->fADC4.number_of_doubles = this->fADC4.number_of_doubles;
	clone->fADC4.GroupEndMarker = this->fADC4.GroupEndMarker;
	clone->fADC4.driver_version = this->fADC4.driver_version;
	clone->fADC4.i32NumberOfDAQLoops = this->fADC4.i32NumberOfDAQLoops;
	clone->fADC4.bReadCustomData = this->fADC4.bReadCustomData;
	clone->fADC4.i32NumberOfADCmodules = this->fADC4.i32NumberOfADCmodules;
	clone->fADC4.iTriggerChannel = this->fADC4.iTriggerChannel;
	clone->fADC4.dGroupRangeStart = this->fADC4.dGroupRangeStart;
	clone->fADC4.dGroupRangeEnd = this->fADC4.dGroupRangeEnd;
	clone->fADC4.csConfigFile = this->fADC4.csConfigFile;
	clone->fADC4.csINLFile = this->fADC4.csINLFile;
	clone->fADC4.csDNLFile = this->fADC4.csDNLFile;
	for (__int32 i = 0; i < 20; i++) clone->fADC4.bits_per_mVolt[i] = this->fADC4.bits_per_mVolt[i];

	return true;
}






//////////////////////////////////////////////////////////////////
// decompress_asynchronous_fADC8_signal()
//////////////////////////////////////////////////////////////////

bool LMF_IO::decompress_asynchronous_fADC8_signal(fADC8_signal_info_struct & signal_info, unsigned __int32 source_buffer[], unsigned __int32 source_buffer_size_in_32bit_words, __int16 i16bit_target_buffer[], __int32 target_buffer_size_in_16bit_words, __int32& number_of_filled_16bit_words)
{
	number_of_filled_16bit_words = -signal_info.timestamp_subindex - 1;

	if ((signal_info.signal_type == FADC8_HEADER_EVENT_ID_TDC) || (signal_info.signal_type == FADC8_HEADER_EVENT_ID_END_MARKER)) {
		number_of_filled_16bit_words = 0;
		return false;
	}

	unsigned __int32 limit_;
	if (signal_info.signallength_including_header_in_32bit_words - 4 < __int32(source_buffer_size_in_32bit_words)) {
		limit_ = signal_info.signallength_including_header_in_32bit_words - 4;
	}
	else {
		limit_ = source_buffer_size_in_32bit_words;
	}

	if ((signal_info.signal_type == FADC8_HEADER_EVENT_ID_1_25G_ADC1)
		|| (signal_info.signal_type == FADC8_HEADER_EVENT_ID_1_25G_ADC2)
		|| (signal_info.signal_type == FADC8_HEADER_EVENT_ID_1_25G_ADC3)
		|| (signal_info.signal_type == FADC8_HEADER_EVENT_ID_1_25G_ADC4)) {

		for (unsigned __int32 i = 4; i < limit_ + 4; i += 4) {
			if (target_buffer_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 3) {
				break;
			}
			for (__int32 j = 0; j < 4; j++) {
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + j] >> 20) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + j] >> 10) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + j]) & 0x3ff;
			}
		}

		number_of_filled_16bit_words++;
		//trace_filter(i16bit_target_buffer,number_of_filled_16bit_words, signal_info);
		return true;
	} // endif 1.25 GS mode


	if ((signal_info.signal_type == FADC8_HEADER_EVENT_ID_2_5G_ADC12)
		|| (signal_info.signal_type == FADC8_HEADER_EVENT_ID_2_5G_ADC34)) {

		for (unsigned __int32 i = 4; i < limit_ + 4; i += 8) {
			if (target_buffer_size_in_16bit_words < number_of_filled_16bit_words + 1 + 2 * 4 * 3) {
				break;
			}

			for (__int32 j = 0; j < 4; j++) {
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> 20) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> 20) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> 10) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> 10) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j]) & 0x3ff;
				i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j]) & 0x3ff;
			}

		}

		number_of_filled_16bit_words++;
		//trace_filter(i16bit_target_buffer,number_of_filled_16bit_words, signal_info);
		return true;
	} // endif 2.5 Gs mode

	if (signal_info.signal_type == FADC8_HEADER_EVENT_ID_5G_ADC1234) {

		for (unsigned __int32 i = 4; i < limit_ + 4; i += 16) {
			if (target_buffer_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 4 * 3) {
				break;
			}

			for (__int32 j = 0; j < 4; j++) {
				for (__int32 shift_ = 20; shift_ >= 0; shift_ -= 10) {
					i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 8 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 12 + j] >> shift_) & 0x3ff;
				}
			}

		}

		number_of_filled_16bit_words++;
		//trace_filter(i16bit_target_buffer,number_of_filled_16bit_words, signal_info);
		return true;
	} // endif 5 Gs mode

	return false;
}



















//////////////////////////////////////////////////////////////////
// decompress_synchronous_fADC8_signal()
//////////////////////////////////////////////////////////////////

bool LMF_IO::decompress_synchronous_fADC8_signal(fADC8_signal_info_struct & signal_info, unsigned __int32 source_buffer[], unsigned __int32 source_buffer_size_in_32bit_words, __int32& number_of_filled_16bit_words,
	__int16 i16bit_target_buffer1[], __int32 target_buffer1_size_in_16bit_words,
	__int16 i16bit_target_buffer2[], __int32 target_buffer2_size_in_16bit_words,
	__int16 i16bit_target_buffer3[], __int32 target_buffer3_size_in_16bit_words,
	__int16 i16bit_target_buffer4[], __int32 target_buffer4_size_in_16bit_words)
{

	number_of_filled_16bit_words = -1;

	if (signal_info.signal_type != FADC8_HEADER_EVENT_ID_5G_ADC1234) {
		number_of_filled_16bit_words = 0;
		return false;
	}

	unsigned __int32 limit_;
	if (signal_info.signallength_including_header_in_32bit_words - 4 < __int32(source_buffer_size_in_32bit_words)) {
		limit_ = signal_info.signallength_including_header_in_32bit_words - 4;
	}
	else {
		limit_ = source_buffer_size_in_32bit_words;
	}


	if (signal_info.megasamples_per_second == 5000) {

		for (unsigned __int32 i = 4; i < limit_ + 4 - 16; i += 16) { // xxx stimmt -16?
			if (target_buffer1_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 4 * 3) break;

			for (__int32 j = 0; j < 4; j++) {
				for (__int32 shift_ = 20; shift_ >= 0; shift_ -= 10) {
					i16bit_target_buffer1[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer1[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 8 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer1[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer1[(++number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 12 + j] >> shift_) & 0x3ff;
				}
			}

		}
		number_of_filled_16bit_words++;
		//trace_filter(i16bit_target_buffer1,number_of_filled_16bit_words, signal_info);
		return true;
	}





	if (signal_info.megasamples_per_second == 2500) {
		for (unsigned __int32 i = 4; i < limit_ + 4 - 16; i += 16) {
			if (target_buffer1_size_in_16bit_words < number_of_filled_16bit_words + 1 + 2 * 4 * 3) break;
			if (target_buffer3_size_in_16bit_words < number_of_filled_16bit_words + 1 + 2 * 4 * 3) break;

			for (__int32 j = 0; j < 4; j++) {
				for (__int32 shift_ = 20; shift_ >= 0; shift_ -= 10) {
					++number_of_filled_16bit_words;
					i16bit_target_buffer1[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer3[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 8 + j] >> shift_) & 0x3ff;

					++number_of_filled_16bit_words;
					i16bit_target_buffer1[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer3[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 12 + j] >> shift_) & 0x3ff;
				}
			}

		}
		//trace_filter(i16bit_target_buffer1,number_of_filled_16bit_words, signal_info);
		//trace_filter(i16bit_target_buffer3,number_of_filled_16bit_words, signal_info);
		number_of_filled_16bit_words++;
		return true;
	}


	if (signal_info.megasamples_per_second == 1250) {
		for (unsigned __int32 i = 4; i < limit_ + 4 - 16; i += 16) {
			if (target_buffer1_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 3) break;
			if (target_buffer2_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 3) break;
			if (target_buffer3_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 3) break;
			if (target_buffer4_size_in_16bit_words < number_of_filled_16bit_words + 1 + 4 * 3) break;

			for (__int32 j = 0; j < 4; j++) {
				for (__int32 shift_ = 20; shift_ >= 0; shift_ -= 10) {
					++number_of_filled_16bit_words;
					i16bit_target_buffer1[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 0 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer2[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 4 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer3[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 8 + j] >> shift_) & 0x3ff;
					i16bit_target_buffer4[(number_of_filled_16bit_words) > 0 ? number_of_filled_16bit_words : 0] = (source_buffer[i + 12 + j] >> shift_) & 0x3ff;
				}
			}

		}
		//trace_filter(i16bit_target_buffer1,number_of_filled_16bit_words, signal_info);
		//trace_filter(i16bit_target_buffer2,number_of_filled_16bit_words, signal_info);
		//trace_filter(i16bit_target_buffer3,number_of_filled_16bit_words, signal_info);
		//trace_filter(i16bit_target_buffer4,number_of_filled_16bit_words, signal_info);
		number_of_filled_16bit_words++;
		return true;
	}

	number_of_filled_16bit_words = 0;
	return false;
}



