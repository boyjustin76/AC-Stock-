<#
    AE 의 최상위 창을 열거하고, 걸려 있는 모달을 밖에서 닫는다.

        .	oolse\wins.ps1            창 목록만 본다
        .	oolse\wins.ps1 -Close     visible+enabled 인 #32770 에 WM_CLOSE 를 보낸다

    모달이 뜨면 BridgeTalk 잡이 TIMEOUT 난다. AE 는 프리미어와 달리 '모달이라 못 돈다' 고
    깨끗하게 알려 주지만, 그래도 사람이 닫기 전엔 아무것도 못 한다. 이걸로 밖에서 닫는다.
    (프리미어 M6 에서 '새 시퀀스' 모달을 닫을 때 쓴 방법 그대로다.)
#>
param([switch]$Close)

Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class Win2 {
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
  public static List<string> ForPid(uint want) {
    var outp = new List<string>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p == want) {
        var t = new StringBuilder(512); GetWindowTextW(h, t, 512);
        var c = new StringBuilder(256); GetClassNameW(h, c, 256);
        outp.Add(string.Format("vis={0,-5} en={1,-5} cls={2,-24} [{3}]",
          IsWindowVisible(h), IsWindowEnabled(h), c.ToString(), t.ToString()));
      }
      return true;
    }, IntPtr.Zero);
    return outp;
  }
}
"@


Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class Dlg {
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, IntPtr l, uint f, uint t, out IntPtr r);
  const uint WM_CLOSE = 0x0010;
  public static List<string> CloseDialogs(uint want) {
    var log = new List<string>();
    var hits = new List<IntPtr>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p != want) return true;
      var c = new StringBuilder(256); GetClassNameW(h, c, 256);
      if (c.ToString() == "#32770" && IsWindowVisible(h) && IsWindowEnabled(h)) hits.Add(h);
      return true;
    }, IntPtr.Zero);
    foreach (var h in hits) {
      var t = new StringBuilder(512); GetWindowTextW(h, t, 512);
      IntPtr r;
      SendMessageTimeout(h, WM_CLOSE, IntPtr.Zero, IntPtr.Zero, 2, 3000, out r);
      log.Add("WM_CLOSE -> [" + t.ToString() + "]");
    }
    if (hits.Count == 0) log.Add("닫을 대화상자 없음");
    return log;
  }
}
"@
$p = Get-Process AfterFX -ErrorAction SilentlyContinue
if (-not $p) { 'AE 안 떠 있음'; exit }
if ($Close) { [Dlg]::CloseDialogs([uint32]$p.Id) } else { [Win2]::ForPid([uint32]$p.Id) }
