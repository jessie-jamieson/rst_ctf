#!/usr/bin/env python3
"""Single, deliberate OPC-UA write to one node, with read-back confirmation.

SAFETY: dry-run by DEFAULT. It reads the node's current value and type and
prints what it *would* write, but does NOT write unless you pass --commit.
This targets LIVE hardware (an acid-dosing skid) -- review before committing.

Usage:
  opcua_write.py <host> <nodeid> <value>            # dry-run preview (no write)
  opcua_write.py <host> <nodeid> <value> --commit   # actually write + read back

NodeId examples:  "ns=3;s=\"DosingDB\".\"AcidPump\""   or   "ns=4;i=12"
Value is coerced to the node's data type (bool/int/float/string).
"""
import asyncio, sys
from asyncua import Client, ua

def parse_args(argv):
    commit = "--commit" in argv
    pos = [a for a in argv[1:] if a != "--commit"]
    if len(pos) < 3:
        print(__doc__); sys.exit(2)
    return pos[0], pos[1], pos[2], commit

def coerce(value_str, vtype):
    name = vtype.name if hasattr(vtype, "name") else str(vtype)
    if name == "Boolean":
        return value_str.strip().lower() in ("1", "true", "on", "yes", "t")
    if name in ("Float", "Double"):
        return float(value_str)
    if name.startswith("Int") or name.startswith("UInt") or name in ("Byte", "SByte"):
        return int(value_str)
    return value_str  # String / other

async def main():
    host, nodeid, value_str, commit = parse_args(sys.argv)
    url = f"opc.tcp://{host}:4840"
    c = Client(url)
    await c.connect()
    try:
        node = c.get_node(nodeid)
        try:
            bn = (await node.read_browse_name()).Name
        except Exception:
            bn = "?"
        vtype = await node.read_data_type_as_variant_type()
        before = await node.read_value()
        new_val = coerce(value_str, vtype)
        print(f"node   : {nodeid}  ({bn})")
        print(f"type   : {vtype.name}")
        print(f"before : {before!r}")
        print(f"to-write: {new_val!r}")
        if not commit:
            print("\nDRY-RUN: no write performed. Re-run with --commit to actuate.")
            return
        await node.write_value(ua.DataValue(ua.Variant(new_val, vtype)))
        after = await node.read_value()
        print(f"after  : {after!r}")
        print("OK" if after == new_val else "WROTE (read-back differs — logic may be overriding it)")
    finally:
        await c.disconnect()

asyncio.run(main())
