#!/usr/bin/env python3
"""READ-ONLY OPC-UA recon for the S7-1200 at opc.tcp://<host>:4840.
Discovers endpoints/security, lists namespaces, and walks the object tree
printing each node's BrowseName, NodeId, class, and for variables the value
and AccessLevel (R/W). No writes. Bounded depth/node count. Tees to a file.
Usage: opcua_browse.py [host]
"""
import asyncio, sys, os, datetime
from asyncua import Client, ua
from asyncua.ua import NodeClass

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.100.56"
URL = f"opc.tcp://{HOST}:4840"
MAX_DEPTH = 7
MAX_NODES = 600

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opcua_browse_out.txt")
_f = open(OUT, "w")
def out(*a):
    s = " ".join(str(x) for x in a)
    print(s); _f.write(s + "\n"); _f.flush()

def access_str(al):
    # ua.AccessLevel.* are BIT POSITIONS (CurrentRead=0, CurrentWrite=1); shift to masks.
    parts = []
    if al & (1 << int(ua.AccessLevel.CurrentRead)):  parts.append("R")
    if al & (1 << int(ua.AccessLevel.CurrentWrite)): parts.append("W")
    return "".join(parts) or "-"

async def endpoints():
    out(f"== endpoints @ {URL} ==")
    c = Client(URL)
    try:
        eps = await c.connect_and_get_server_endpoints()
        for ep in eps:
            mode = ep.SecurityMode
            tokens = [t.TokenType.name for t in ep.UserIdentityTokens]
            out(f"  policy={ep.SecurityPolicyUri.split('#')[-1]} mode={mode} "
                f"url={ep.EndpointUrl} tokens={tokens}")
    except Exception as e:
        out("  endpoint discovery error:", repr(e))

async def walk(node, depth, counter):
    if counter[0] >= MAX_NODES or depth > MAX_DEPTH:
        return
    counter[0] += 1
    try:
        bn = (await node.read_browse_name()).Name
    except Exception:
        bn = "?"
    try:
        nclass = await node.read_node_class()
    except Exception:
        nclass = None
    nid = node.nodeid.to_string()
    line = f"  {'  '*depth}{bn} [{nclass.name if nclass else '?'}] {nid}"
    if nclass == NodeClass.Variable:
        try:
            val = await node.read_value()
        except Exception as e:
            val = f"<read err {type(e).__name__}>"
        try:
            al = await node.read_attribute(ua.AttributeIds.AccessLevel)
            acc = access_str(al.Value.Value)
        except Exception:
            acc = "?"
        line += f"  ({acc}) = {val!r}"
    out(line)
    if nclass in (NodeClass.Object, NodeClass.Variable, None):
        try:
            for ch in await node.get_children():
                await walk(ch, depth + 1, counter)
        except Exception:
            pass

async def browse():
    out(f"\n== browse (anonymous, security None) ==")
    c = Client(URL)
    try:
        await c.connect()
    except Exception as e:
        out("  connect failed:", repr(e)); return
    try:
        try:
            ns = await c.get_namespace_array()
            out("  namespaces:")
            for i, u in enumerate(ns): out(f"    [{i}] {u}")
        except Exception as e:
            out("  namespace read err:", repr(e))
        out("  --- Objects tree ---")
        objects = c.nodes.objects
        counter = [0]
        for ch in await objects.get_children():
            bn = (await ch.read_browse_name()).Name
            if bn == "Server":   # skip standard diagnostics subtree (noise)
                out(f"  (skipping standard Server node {ch.nodeid.to_string()})")
                continue
            await walk(ch, 0, counter)
        out(f"  [walked {counter[0]} nodes, cap {MAX_NODES}]")
    finally:
        await c.disconnect()

async def main():
    out(f"# opcua_browse {datetime.datetime.now()} host={HOST}")
    await endpoints()
    await browse()
    out("\n[done]")

asyncio.run(main())
