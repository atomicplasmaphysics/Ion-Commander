#define _CRT_SECURE_NO_WARNINGS
#include "LMF_IO.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>

#include <string.h>
#include <stdio.h>

char* optarg;
int optind = 1;
int opterr, optopt;

int custom_getopt(int argc, char* argv[], const char* optstring) {
    static int index = optind;
    const char* opt;

    optarg = NULL;

    if (index >= argc || argv[index][0] != '-' || argv[index][1] == '\0')
        return -1;

    if (argv[index][1] == '-' && argv[index][2] == '\0') {
        ++index;
        return -1;
    }

    opt = strchr(optstring, argv[index][1]);

    if (opt == NULL)
        return '?';

    if (opt[1] == ':') {
        if (argv[index][2] != '\0') {
            optarg = &argv[index][2];
        }
        else {
            ++index;
            if (index >= argc || argv[index][0] == '-') {
                return '?';
            }
            optarg = argv[index];
        }
    }

    ++index;
    return opt[0];
}


#define NUM_CHANNELS 80
#define NUM_IONS 100

void splitOnLastDot(const char* input, char* before_dot, char* after_dot) {
    // Find the last occurrence of '.' and split input string there

    const char* last_dot = strrchr(input, '.');

    if (last_dot != NULL) {
        size_t before_length = last_dot - input;
        strncpy(before_dot, input, before_length);
        before_dot[before_length] = '\0';
        strcpy(after_dot, last_dot + 1);
    }
    else {
        strcpy(before_dot, input);
        after_dot[0] = '\0';
    }
}


void printUsage(char** argv) {
    // prints the usage of the program

    printf("Usage: %s <input_file> [options]\n", argv[0]);
    printf("Options:\n");
    printf("  -o <arg>  Name of output file.\n");
    printf("  -H        Creates a histogram file with TDC bin width.\n");
    printf("  -a <arg>  Limiting start time in [s].\n");
    printf("  -b <arg>  Limiting end time in [s].\n");
    printf("  -s <arg>  Splits into x parts.\n");
    printf("  -S <arg>  Splits every x seconds.\n");
    printf("  -v        Enables verbose output.\n");
    printf("  -h        Display this information.\n");
    printf("  -t        Include trigger channel.\n");
    printf("  -r        Include rising edges.\n");
    printf("  -m        Output amplitude.\n");
}

void writeHeader(FILE* outfile, double tdcresolution, unsigned int number_of_channels, double group_range_start, double group_range_end, int number_of_bins, __int32 trigger_channel, time_t starttime, time_t stoptime) {
    fprintf(outfile, "TDC resolution = %lf ps\n", tdcresolution * 1.e3);
    fprintf(outfile, "Number of channels = %d\n", number_of_channels);
    fprintf(outfile, "Group range start = %lf ns\n", group_range_start);
    fprintf(outfile, "Group range end = %lf ns\n", group_range_end);
    fprintf(outfile, "Number of max bins = %d\n", number_of_bins);
    fprintf(outfile, "Trigger channel = %d\n", trigger_channel);
    fprintf(outfile, "Start time = %s", ctime(&starttime));
    fprintf(outfile, "Stop time =  %s", ctime(&stoptime));
    fprintf(outfile, "\n");
    fprintf(outfile, "Eventnumber\tChannelnumber\tStarttime[ms]\tTOF[ns]\tIsFalling\tAmplitude[ns]\n");
}


int main(int argc, char* argv[]) {

    // user parameters and flags
    char input_filename[500] = { 0 };

    char output_flag = 0;
    char current_output_filename[500] = { 0 };
    char output_filename[500] = { 0 };
    char output_file_extension[100] = { 0 };

    char histogram_flag = 0;
    unsigned __int32* histogram;

    char timing_flag = 0;
    char start_time_flag = 0;
    double start_time_set = 0;
    double start_time = 0;
    char end_time_flag = 0;
    double end_time_set = 0;
    double end_time = 0;


    char split_flag = 0;
    int split_splits = 0;

    char split_seconds_flag = 0;
    double split_seconds_splits = 0;

    char verbose_flag = 0;

    char trigger_channel_flag = 0;

    char rising_edge_flag = 0;

    char amplitude_flag = 0;

    if (argc < 2) {
        printf("ERROR: Invalid arguments\n");
        printUsage(argv);
        return 1;
    }

    sprintf(input_filename, "%s", (char*)argv[1]);

    // Parse input parameters using getopt
    int opt;
    optind = 2;
    // HINT: do not forget to include "letters" here
    while ((opt = custom_getopt(argc, argv, "o:Ha:b:s:S:vhtrm")) != -1) {
        switch (opt) {
        case 'o':
            output_flag = 1;
            snprintf(output_filename, sizeof(output_filename), "%s", optarg);
            break;
        case 'H':
            histogram_flag = 1;
            break;
        case 'a':
            start_time_flag = 1;
            start_time_set = atof(optarg);
            start_time = start_time_set;
            break;
        case 'b':
            end_time_flag = 1;
            end_time_set = atof(optarg);
            end_time = end_time_set;
            break;
        case 's':
            split_flag = 1;
            split_splits = atoi(optarg);
            break;
        case 'S':
            split_seconds_flag = 1;
            split_seconds_splits = atof(optarg);
            break;
        case 'v':
            verbose_flag = 1;
            break;
        case 'h':
            printUsage(argv--);
            return 0;
        case 't':
            trigger_channel_flag = 1;
            break;
        case 'r':
            rising_edge_flag = 1;
            break;
        case 'm':
            amplitude_flag = 1;
            break;
        default:
            return 1;
        }
    }

    if (start_time_flag + end_time_flag == 1) {
        printf("ERROR: Only start-time (-a) or end-time (-b) provided.\n");
        return 1;
    }

    if (split_flag + split_seconds_flag == 2) {
        printf("ERROR: Only splits (-s) or splits-seconds (-S) can be provided.\n");
        return 1;
    }

    if (start_time_flag + end_time_flag == 2) {
        if (end_time > start_time) {
            timing_flag = 1;
            if (verbose_flag) {
                printf("Limiting between %f and %f seconds.\n", start_time, end_time);
            }
        }
        else {
            printf("ERROR: End time before start time.\n");
            return 1;
        }
    }

    if (histogram_flag && verbose_flag) {
        printf("INFO: Will output histogram data.\n");
    }

    if (!output_flag) {
        splitOnLastDot(input_filename, current_output_filename, output_file_extension);
        if (histogram_flag) {
            sprintf(output_file_extension, "cod2");
        }
        else {
            sprintf(output_file_extension, "lmftxt");
        }
    }
    else {
        splitOnLastDot(output_filename, current_output_filename, output_file_extension);
    }

    if (verbose_flag) {
        printf("INFO: Input file: %s\n", input_filename);
    }

    // read LMF
    LMF_IO* LMF = new LMF_IO(NUM_CHANNELS, NUM_IONS);
    unsigned __int64 LMF_position;

    if (!LMF->OpenInputLMF(input_filename)) {
        printf("ERROR: Code %i: %s\n", LMF->errorflag, LMF->error_text[LMF->errorflag]);
        return 1;
    }

    // header information
    char error_text[512] = { 0 };
    double tdcresolution = LMF->tdcresolution;
    unsigned int number_of_channels = LMF->GetNumberOfChannels();
    __int32 trigger_channel = LMF->TDC8HP.TriggerChannel_p64;
    double group_range_start = LMF->TDC8HP.GroupRangeStart_p69;
    double group_range_end = LMF->TDC8HP.GroupRangeEnd_p70;
    int number_of_bins = (int)((group_range_end - group_range_start) / tdcresolution);
    int number_of_bin;
    histogram = (unsigned __int32*)malloc(number_of_bins * sizeof(unsigned __int32));
    if (histogram == NULL) {
        printf("ERROR: Could not allocate shit.\n");
        return 1;
    }

    double first_timestamp = 0;
    double last_timestamp = 0;
    double new_timestamp;
    unsigned __int64 event_counter = 0;
    unsigned __int64 event_counter_max = LMF->uint64_Numberofevents;
    unsigned __int64 last_event_counter = 0;
    unsigned __int64 split_event_counter;

    if (split_flag) {
        split_event_counter = (int)event_counter_max / split_splits + 1;
    }

    unsigned __int32* number_of_hits;
    number_of_hits = LMF->number_of_hits;
    __int32* i32TDC;
    i32TDC = LMF->i32TDC;
    __int32 iTDCij;
    bool* bIsFallingTDC;
    bIsFallingTDC = LMF->bIsFallingTDC;
    bool bIsFalling;

    bool bLastIsFalling;
    __int32 iLastiTDCij;
    double amplitude = -1;

    unsigned int i, j;
    unsigned int split_counter = 0;

    if (verbose_flag) {
        printf("INFO: Event counter (max) = %lld\n", event_counter_max);
    }

    while (1) {
        // reset histogram
        memset(histogram, 0, number_of_bins * sizeof(unsigned __int32));

        // get output file
        if (split_flag) {
            sprintf(output_filename, "%s_%d.%s", current_output_filename, split_counter + 1, output_file_extension);
        }
        else if (split_seconds_flag) {
            start_time = start_time_set + split_seconds_splits * split_counter;
            end_time = start_time_set + split_seconds_splits * (split_counter + 1);
            timing_flag = 1;
            sprintf(output_filename, "%s_%ds-%ds.%s", current_output_filename, (int)start_time, (int)end_time, output_file_extension);
        }
        else {
            sprintf(output_filename, "%s.%s", current_output_filename, output_file_extension);
        }
        if (verbose_flag) {
            printf("INFO: Output file: %s\n", output_filename);
        }
        FILE* outfile = fopen(output_filename, "wt");
        if (outfile == NULL) {
            printf("ERROR: Could not open output file.\n");
            return 1;
        }

        // write header
        if (!histogram_flag) {
            writeHeader(outfile, tdcresolution, number_of_channels, group_range_start, group_range_end, number_of_bins, trigger_channel, LMF->Starttime, LMF->Stoptime);
        }

        // go to position
        if (split_flag + split_seconds_flag != 0 && split_counter != 0) {
            LMF->input_lmf->seek(LMF_position);
        }

        // data
        while (1) {
            if (LMF->ReadNextEvent()) {
                bLastIsFalling = false;
                iLastiTDCij = 0;

                // check error flag
                if (LMF->errorflag) {
                    LMF->GetErrorText(LMF->errorflag, error_text);
                    printf("ERROR: %s\n", error_text);
                    return 1;
                }

                // increase event counter
                event_counter++;
                if (verbose_flag && event_counter % 100000 == 0) {
                    printf("INFO: Event counter = %lld (%.1f%%)\n", event_counter, (double)event_counter / event_counter_max * 100);
                    fflush(stdout);
                }

                // get timestamp
                new_timestamp = LMF->DOUBLE_timestamp;
                if (first_timestamp == 0.) first_timestamp = new_timestamp;
                new_timestamp -= first_timestamp;
                last_timestamp = new_timestamp;

                // exclude some events that are not in given time
                if (timing_flag) {
                    if (new_timestamp < start_time) {
                        continue;
                    }
                    if (new_timestamp > end_time) {
                        LMF_position = LMF->input_lmf->tell();
                        break;
                    }
                }

                // check if we have too many events already
                if (split_flag) {
                    if (event_counter - last_event_counter > split_event_counter) {
                        last_event_counter = event_counter;
                        event_counter--;
                        LMF_position = LMF->input_lmf->tell();
                        break;
                    }
                }

                // actual TOF calculation
                for (i = 0; i < number_of_channels; i++) {
                    // skip trigger channel
                    if (!trigger_channel_flag) {
                        if (i + 1 == trigger_channel) {
                            continue;
                        }
                    }

                    // handle every channel individually
                    for (j = 0; j < number_of_hits[i]; j++) {
                        iTDCij = i32TDC[i * NUM_IONS + j];
                        bIsFalling = bIsFallingTDC[i * NUM_IONS + j];

                        // add to histogram
                        if (histogram_flag) {
                            // check if rising edge
                            if (!bIsFalling && !rising_edge_flag) { continue; }

                            // insert into histogram
                            number_of_bin = (int)((iTDCij * tdcresolution - group_range_start) / tdcresolution);
                            if (number_of_bin < 0 || number_of_bin >= number_of_bins) {
                                printf("WARNING: Error occured while trying to get bin number of histogram. Skipping...\n");
                                continue;
                            }
                            histogram[number_of_bin]++;
                        }

                        // print directly to file
                        else {
                            // check if we need amplitude calculated
                            if (amplitude_flag) {
                                // do fallig falag magic
                                if (bIsFalling) { amplitude = -1; }
                                else {
                                    if (!bLastIsFalling) { amplitude = -1; }
                                    else { amplitude = (iTDCij - iLastiTDCij) * tdcresolution; }
                                }

                                bLastIsFalling = bIsFalling;
                                iLastiTDCij = iTDCij;
                            }

                            // write to output file
                            fprintf(outfile, "%lld\t%d\t%.3lf\t%.3lf\t%d\t%.3lf\n",
                                event_counter, i + 1, new_timestamp * 1.e3, iTDCij * tdcresolution, bIsFalling, amplitude);
                        }
                    }
                }
            }

            // check error flag
            if (LMF->errorflag) break;
        }
        if (verbose_flag) {
            printf("INFO: Event counter = %lld (%.1f%%)\n", event_counter, (double)event_counter / event_counter_max * 100);
            fflush(stdout);
        }

        // output histogram
        if (histogram_flag) {
            for (i = 0; i < (unsigned int)number_of_bins; i++) {
                fprintf(outfile, "%e,%d\n", group_range_start + i * tdcresolution, histogram[i]);
            }
        }

        // close outputfile
        if (outfile) fclose(outfile);

        // check error flag
        if (LMF->errorflag) break;

        // break while loop
        if (split_flag + split_seconds_flag == 0) {
            break;
        }
        split_counter++;
    }

    // cleanup
    if (LMF) delete LMF;
    free(histogram);

    return 0;
}




// Programm ausführen: STRG+F5 oder Menüeintrag "Debuggen" > "Starten ohne Debuggen starten"
// Programm debuggen: F5 oder "Debuggen" > Menü "Debuggen starten"

// Tipps für den Einstieg: 
//   1. Verwenden Sie das Projektmappen-Explorer-Fenster zum Hinzufügen/Verwalten von Dateien.
//   2. Verwenden Sie das Team Explorer-Fenster zum Herstellen einer Verbindung mit der Quellcodeverwaltung.
//   3. Verwenden Sie das Ausgabefenster, um die Buildausgabe und andere Nachrichten anzuzeigen.
//   4. Verwenden Sie das Fenster "Fehlerliste", um Fehler anzuzeigen.
//   5. Wechseln Sie zu "Projekt" > "Neues Element hinzufügen", um neue Codedateien zu erstellen, bzw. zu "Projekt" > "Vorhandenes Element hinzufügen", um dem Projekt vorhandene Codedateien hinzuzufügen.
//   6. Um dieses Projekt später erneut zu öffnen, wechseln Sie zu "Datei" > "Öffnen" > "Projekt", und wählen Sie die SLN-Datei aus.
