import CoreLocation
import CoreWLAN
import Foundation

let LIVE = "/private/tmp/claude-501/-Users-jessiejamieson-Desktop-rst-ctf/18c0fc7e-775e-49af-9bb6-6f477c57e8ba/scratchpad/wifi_live.txt"
let TARGET_BSSID = "b8:fb:b3:98:91:de"
let TARGET_SSID  = "secret plutonium stash"

func emit(_ s: String) {
    let line = s + "\n"
    if let fh = FileHandle(forWritingAtPath: LIVE) {
        fh.seekToEndOfFile(); fh.write(line.data(using: .utf8)!); fh.closeFile()
    } else {
        try? line.data(using: .utf8)!.write(to: URL(fileURLWithPath: LIVE))
    }
    FileHandle.standardOutput.write(line.data(using: .utf8)!)
}

func bar(_ rssi: Int) -> String {
    let n = max(0, min(20, (rssi + 95) * 20 / 65))   // -95..-30 -> 0..20 blocks
    return "[" + String(repeating: "#", count: n) + String(repeating: ".", count: 20 - n) + "]"
}

func authorized(_ s: CLAuthorizationStatus) -> Bool { s.rawValue == 3 || s.rawValue == 4 }

final class Hunter: NSObject, CLLocationManagerDelegate {
    let lm = CLLocationManager()
    let iface = CWWiFiClient.shared().interface()
    var last: Int? = nil
    var best: Int = -200
    var started = false

    override init() { super.init(); lm.delegate = self }

    func begin() {
        lm.requestAlwaysAuthorization()
        lm.startUpdatingLocation()
        if authorized(lm.authorizationStatus) { startTimer() }
    }

    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        if authorized(m.authorizationStatus) { startTimer() }
        else if m.authorizationStatus == .denied { emit("AUTH DENIED - re-grant iTerm/WifiScan location"); exit(2) }
    }

    func startTimer() {
        if started { return }
        started = true
        try? "".data(using: .utf8)!.write(to: URL(fileURLWithPath: LIVE))
        emit("Fox-hunt live. Target \(TARGET_BSSID) (ch 9, 2.4GHz). One reading ~1.5s. Close window to stop.")
        emit("rssi: higher (closer to 0) = closer.  peak = strongest spot you have hit so far.")
        emit("")
        // Timer on the main run loop keeps the process alive.
        let t = Timer(timeInterval: 1.5, repeats: true) { [weak self] _ in self?.sweep() }
        RunLoop.main.add(t, forMode: .common)
        sweep()
    }

    func sweep() {
        guard let iface = iface else { emit("no wifi interface"); return }
        var found: CWNetwork? = nil
        if let nets = try? iface.scanForNetworks(withName: nil) {
            for n in nets where (n.bssid ?? "").lowercased() == TARGET_BSSID { found = n; break }
            if found == nil {
                for n in nets where (n.ssid ?? "").lowercased() == TARGET_SSID { found = n; break }
            }
        }
        let fmt = DateFormatter(); fmt.dateFormat = "HH:mm:ss"
        let t = fmt.string(from: Date())
        guard let n = found else {
            emit("\(t)  -- not seen this sweep (too far or blocked) - keep moving --")
            return
        }
        let r = n.rssiValue
        var trend = "----  "
        if let l = last {
            if r >= l + 2 { trend = "WARMER" }
            else if r <= l - 2 { trend = "colder" }
            else { trend = "same  " }
        }
        last = r
        if r > best { best = r }
        emit(String(format: "%@  rssi=%-4d %@  %@   peak=%-4d", t, r, bar(r), trend, best))
    }
}

let h = Hunter()
h.begin()
RunLoop.main.run()   // runs forever; the repeating timer keeps it alive
