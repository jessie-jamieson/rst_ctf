// CoreWLAN WiFi scanner for the "Secret Plutonium Stash" challenge.
// Prints every visible BSS: SSID, BSSID (AP MAC), channel, band, RSSI.
// SSID/BSSID are nil unless the controlling app (iTerm) has Location Services.
//
// Run:  swift scan.swift            (optional: swift scan.swift Plutonium  to highlight)

import CoreWLAN
import Foundation

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

let needle = CommandLine.arguments.dropFirst().first?.lowercased()

guard let iface = CWWiFiClient.shared().interface() else {
    FileHandle.standardError.write("No Wi-Fi interface found.\n".data(using: .utf8)!)
    exit(1)
}

do {
    let nets = try iface.scanForNetworks(withName: nil)
    print("Scanned \(nets.count) BSS. Interface: \(iface.interfaceName ?? "?")\n")
    let rows = nets.sorted { $0.rssiValue > $1.rssiValue }
    var sawNil = false
    for n in rows {
        let ssid = n.ssid ?? "<nil-needs-location>"
        let bssid = n.bssid ?? "<nil-needs-location>"
        if n.ssid == nil || n.bssid == nil { sawNil = true }
        let ch = n.wlanChannel
        let chNum = ch?.channelNumber ?? -1
        let band = bandName(ch)
        let mark = (needle != nil && ssid.lowercased().contains(needle!)) ? "  <<< MATCH" : ""
        print(String(format: "%-28@  bssid=%-18@  ch=%-3d %-6@  rssi=%-4d%@",
                     ssid as NSString, bssid as NSString, chNum, band as NSString, n.rssiValue, mark))
    }
    if sawNil {
        FileHandle.standardError.write(
          "\nNOTE: some SSID/BSSID are nil. Grant iTerm Location Services, then re-run.\n"
          .data(using: .utf8)!)
    }
} catch {
    FileHandle.standardError.write("Scan failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}
