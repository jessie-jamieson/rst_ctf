import sys,re
data=open(sys.argv[1],'rb').read()
# Split into HTTP messages at each "POST " start
starts=[m.start() for m in re.finditer(rb'POST /', data)]
starts.append(len(data))
docs=[]
for i in range(len(starts)-1):
    msg=data[starts[i]:starts[i+1]]
    hdr_end=msg.find(b'\r\n\r\n')
    if hdr_end<0: continue
    headers=msg[:hdr_end].decode('latin1')
    body=msg[hdr_end+4:]
    chunked='chunked' in headers.lower()
    if chunked:
        out=bytearray(); pos=0
        while pos<len(body):
            nl=body.find(b'\r\n',pos)
            if nl<0: break
            sz_s=body[pos:nl].split(b';')[0].strip()
            try: sz=int(sz_s,16)
            except: break
            if sz==0: break
            out+=body[nl+2:nl+2+sz]
            pos=nl+2+sz+2
        body=bytes(out)
    docs.append((headers.split('\r\n')[0], body))
# find URF docs
for idx,(line,body) in enumerate(docs):
    j=body.find(b'UNIRAST')
    if j>=0:
        urf=body[j:]
        fn=f"{sys.argv[2]}_doc{idx}.urf"
        open(fn,'wb').write(urf)
        sys.stderr.write(f"{fn}: {len(urf)} bytes  (from: {line})\n")
