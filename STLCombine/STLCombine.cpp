#include <windows.h>
#include <commdlg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FILES 100
#define MAX_PATH_LENGTH 400

// Function prototypes
int openFileDialog(HWND hwnd, wchar_t fileNames[MAX_FILES][MAX_PATH_LENGTH], int* fileCount);
int saveFileDialog(HWND hwnd, wchar_t* outputFile);
void processSTLFiles(wchar_t fileNames[MAX_FILES][MAX_PATH_LENGTH], int fileCount, const wchar_t* outputFile);
void extractFacets(FILE* input, FILE* output);

// Main function
int main() {
    wchar_t fileNames[MAX_FILES][MAX_PATH_LENGTH];
    int fileCount = 0;
    wchar_t outputFile[MAX_PATH_LENGTH];

    // Initialize Windows GUI application
    HWND hwnd = GetConsoleWindow();

    // Open file selection dialog
    if (openFileDialog(hwnd, fileNames, &fileCount) == 0) {
        printf("No input files selected.\n");
        return 1;
    }

    // Print input files
    printf("Input files (%d):\n", fileCount);
    for (int i = 0; i < fileCount; i++) {
        wprintf(L" - %s\n", fileNames[i]);
    }

    // Open save file dialog
    if (saveFileDialog(hwnd, outputFile) == 0) {
        printf("No output file selected.\n");
        return 1;
    }
    printf("\n");

    // Print output file
    wprintf(L"Output file:\n - %s\n\n", outputFile);

    // Process and combine STL files
    processSTLFiles(fileNames, fileCount, outputFile);

    printf("Successfully combined STLs\n");

    return 0;
}

// Function to open a file selection dialog for multiple STL files
int openFileDialog(HWND hwnd, wchar_t fileNames[MAX_FILES][MAX_PATH_LENGTH], int* fileCount) {
    OPENFILENAMEW ofn;
    wchar_t fileBuffer[MAX_FILES * MAX_PATH_LENGTH] = { 0 };

    ZeroMemory(&ofn, sizeof(ofn));
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hwnd;
    ofn.lpstrFilter = L"STL Files\0*.stl\0All Files\0*.*\0";
    ofn.lpstrFile = fileBuffer;
    ofn.nMaxFile = sizeof(fileBuffer) / sizeof(wchar_t);
    ofn.Flags = OFN_ALLOWMULTISELECT | OFN_EXPLORER | OFN_FILEMUSTEXIST;

    if (GetOpenFileNameW(&ofn)) {
        wchar_t* ptr = ofn.lpstrFile;
        wchar_t directory[MAX_PATH_LENGTH];
        wcscpy_s(directory, ptr);
        ptr += wcslen(ptr) + 1;

        if (*ptr == L'\0') { // Single file selected
            wcscpy_s(fileNames[0], directory);
            *fileCount = 1;
        }
        else { // Multiple files selected
            int count = 0;
            while (*ptr) {
                swprintf(fileNames[count], MAX_PATH_LENGTH, L"%s\\%s", directory, ptr);
                ptr += wcslen(ptr) + 1;
                count++;
            }
            *fileCount = count;
        }
        return 1;
    }
    return 0;
}

// Function to open a save file dialog for output STL file
int saveFileDialog(HWND hwnd, wchar_t* outputFile) {
    OPENFILENAMEW ofn;
    ZeroMemory(&ofn, sizeof(ofn));

    outputFile[0] = L'\0';

    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hwnd;
    ofn.lpstrFilter = L"STL Files\0*.stl\0All Files\0*.*\0";
    ofn.lpstrFile = outputFile;
    ofn.nMaxFile = MAX_PATH_LENGTH;
    ofn.Flags = OFN_OVERWRITEPROMPT;
    ofn.lpstrDefExt = L"stl";

    return GetSaveFileNameW(&ofn);
}

// Function to process multiple STL files and combine them into one
void processSTLFiles(wchar_t fileNames[MAX_FILES][MAX_PATH_LENGTH], int fileCount, const wchar_t* outputFile) {
    FILE* outFile = NULL;
    if (_wfopen_s(&outFile, outputFile, L"w") != 0 || !outFile) {
        wprintf(L"ERROR: Cannot create output file %s.\n", outputFile);
        return;
    }

    fwprintf(outFile, L"solid combined_stl\n");

    for (int i = 0; i < fileCount; i++) {
        FILE* inFile = NULL;
        if (_wfopen_s(&inFile, fileNames[i], L"r") != 0 || !inFile) {
            wprintf(L"WARNING: Cannot open %s. Skipping it...\n", fileNames[i]);
            continue;
        }

        wchar_t line[256];
        int insideSolid = 0;

        while (fgetws(line, sizeof(line) / sizeof(wchar_t), inFile)) {
            if (wcsstr(line, L"solid")) {
                insideSolid = 1;
            }
            else if (wcsstr(line, L"endsolid")) {
                insideSolid = 0;
            }
            else if (insideSolid) {
                fwprintf(outFile, L"%s", line);
            }
        }

        fclose(inFile);
    }

    fwprintf(outFile, L"endsolid combined_stl\n");
    fclose(outFile);
}

// Function to extract facet data from an ASCII STL file and append it to output
void extractFacets(FILE* input, FILE* output) {
    char line[256];
    int insideSolid = 0;

    while (fgets(line, sizeof(line), input)) {
        if (strstr(line, "solid")) {
            insideSolid = 1;
        }
        else if (strstr(line, "endsolid")) {
            insideSolid = 0;
        }
        else if (insideSolid) {
            fprintf(output, "%s", line);
        }
    }
}