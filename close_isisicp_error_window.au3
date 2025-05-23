;; close error window from ISISICP left over from system tests of isisicp simulation mode
;; we need to avoid using active window functions as we may have a disconnected remote desktop session
;; see https://www.autoitscript.com/wiki/FAQ#Why_doesn.27t_my_script_work_on_a_locked_workstation.3F
;; see https://www.autoitscript.com/wiki/Function_list
;;
;; must be compiled via
;;
;;       Aut2exe_x64.exe /in close_isisicp_error_window.au3 /out close_isisicp_error_window.exe /console 
;;
;; otherwise cannot write to console
;;
;;  then can be run as e.g.
;;
;;   close_isisicp_error_window.exe
;;

#include <Date.au3>
#include <MsgBoxConstants.au3>

If Not @Compiled Then
    MsgBox($MB_SYSTEMMODAL, "", "This script must be compiled in order to run.")
    Exit
EndIf

ConsoleWrite(_Now() & " Looking for isisicp error window to close" & @CRLF)
While WinWait("ISISICP.EXE", "", 1) <> 0
    ConsoleWrite(_Now() & " Closing isisicp error window" & @CRLF)
    WinClose("ISISICP.EXE")
WEnd
