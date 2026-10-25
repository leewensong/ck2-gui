// Native Win64 launcher: no Python installation, .NET, or shell association needed.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <strsafe.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
    wchar_t root[32768], python[32768], script[32768], command[32768];
    DWORD length = GetModuleFileNameW(NULL, root, ARRAYSIZE(root));
    if (!length || length >= ARRAYSIZE(root)) return 1;
    wchar_t *separator = wcsrchr(root, L'\\');
    if (!separator) return 1;
    *separator = 0;
    if (FAILED(StringCchPrintfW(python, ARRAYSIZE(python), L"%s\\runtime\\pythonw.exe", root)) ||
        FAILED(StringCchPrintfW(script, ARRAYSIZE(script), L"%s\\bootstrap.py", root)) ||
        FAILED(StringCchPrintfW(command, ARRAYSIZE(command), L"\"%s\" -I -B \"%s\" %s", python, script, args))) {
        MessageBoxW(NULL, L"The path or argument list is too long.", L"CorridorKey 2.0", MB_ICONERROR);
        return 1;
    }
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(NULL, L"Please extract the entire ZIP before running.\n请先完整解压压缩包，再运行。\n\nMissing runtime or bootstrap.py.", L"CorridorKey 2.0", MB_ICONERROR);
        return 1;
    }
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_SHOWNORMAL;
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, root, &startup, &process)) {
        MessageBoxW(NULL, L"Unable to start the bundled runtime.\n无法启动内置运行环境，请尝试重新解压。", L"CorridorKey 2.0", MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
