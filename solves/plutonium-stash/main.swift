import CoreLocation
import CoreWLAN
import Foundation

let OUT = "/private/tmp/claude-501/-Users-jessiejamieson-Desktop-rst-ctf/18c0fc7e-775e-49af-9bb6-6f477c57e8ba/scratchpad/wifi_result.txt"
let NEEDLE = "plutonium"

func log(_ s: String) {
    let line = s + "\n"
    if let fh = FileHandle(forWritingAtPath: OUT) {
        fh.seekToEndOfFile(); fh.write(line.data(using: .utf8)!); fh.closeFile()
    } else {
        try? line.data(using: .utf8)!.write(to: URL(fileURLWithPath: OUT))
    }
}

func bandName(_ c: CWChannel?) -> String {
    guard let b = c?.channelBand else { return "?" }
    switch b {
    case .band2GHz: return "2.4GHz"
    case .band5GHz: return "5GHz"
    default:
        if #available(macOS 13.0, *), b == .band6GHz { return "6GHz" }
        return "?"
    }
}

func scanAndExit() {
    guard let iface = CWWiFiClient.shared().interface() else {
        log("ERROR: no Wi-Fi interface"); exit(1)
    }
    do {
        let nets = try iface.scanForNetworks(withName: nil)
        log("SCAN OK: \(nets.count) BSS on \(iface.interfaceName ?? "?")")
        for n in nets.sorted(by: { $0.rssiValue > $1.rssiValue }) {
            let ssid = n.ssid ?? "<nil>"
            let bssid = n.bssid ?? "<nil>"
            let ch = n.wlanChannel
            let mark = ssid.lowercased().contains(NEEDLE) ? "  <<< MATCH" : ""
            log(String(format: "%-28@ bssid=%-18@ ch=%-3d %-6@ rssi=%-4d%@",
                       ssid as NSString, bssid as NSString,
                       ch?.channelNumber ?? -1, bandName(ch) as NSString, n.rssiValue, mark))
        }
        log("DONE")
    } catch {
        log("SCAN FAILED: \(error)")
    }
    exit(0)
}

func authorized(_ s: CLAuthorizationStatus) -> Bool {
    return s.rawValue == 3 || s.rawValue == 4   // authorizedAlways / authorized(when-in-use)
}

final class Del: NSObject, CLLocationManagerDelegate {
    let lm = CLLocationManager()
    override init() { super.init(); lm.delegate = self }
    func start() {
        log("=== WifiScan start, initial auth=\(lm.authorizationStatus.rawValue) ===")
        lm.requestAlwaysAuthorization()
        lm.startUpdatingLocation()
        if authorized(lm.authorizationStatus) { scanAndExit() }
    }
    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        let s = m.authorizationStatus
        log("auth changed -> \(s.rawValue)")
        if authorized(s) { scanAndExit() }
        else if s == .denied || s == .restricted { log("AUTH DENIED"); exit(2) }
    }
}

try? "".data(using: .utf8)!.write(to: URL(fileURLWithPath: OUT)) // truncate
let d = Del()
d.start()
// Give the user time to click Allow on the prompt.
RunLoop.main.run(until: Date().addingTimeInterval(90))
log("TIMEOUT: no authorization within 90s (final auth=\(d.lm.authorizationStatus.rawValue))")
exit(3)
