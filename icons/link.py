from wxPython.wx import wxImageFromStream, wxBitmapFromImage
import cStringIO, zlib


def getData():
    return zlib.decompress(
'x\xda\x01Y\x01\xa6\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x0f\
\x00\x00\x00\x11\x08\x06\x00\x00\x00\x02\n\xf6\xa1\x00\x00\x00\x04sBIT\x08\
\x08\x08\x08|\x08d\x88\x00\x00\x01\x10IDATx\x9c\xa5\x93Q\x8a\x840\x0c\x86\
\x7fe\xdf\x8d2WqXt\x07\xbc\x97\x17\xf2\x02\x1e@f\xdc#\xe8\xab \x82\x888B}\
\xb3\xb6\xfb\xd4\xd2\xa2\xee\x0c\xbb?\x14\x12\x92/Ii\xe3\x10\x11\xfe\xaa\x0f\
e\xcc\xf3,_%\x13\x91c\xfa\xae\x02\x85\x108:\xdb\xb6\xa1i\x1a\x14E\xb1k\xe0\
\x9a\x0eclw\x96eA\xdb\xb6\x88\xa2\x08Y\x96Y\x05,\xf8L\xc30 MS\xe4y\x8e$It\
\x81\x97\xb0\x94\x12a\x18\xc2\xf3<L\xd3\x88\xaa\xaat\xcc!"}g\xc6\x18\x84\x10\
:x\xf7}\xdc\x9eO]\x04\x00\xea\xbaF\x1c\xc7 "\xc7\xeal\x82*\xf9\xee\xfb\xda\
\x16Bh\x1b0\x9eJJ\xa9\x03\x8f \xb0F\x7f\x04\x01\xbe\xa6\xc9\xca\xb1`\xb3@4\
\x8e\x00\x80\xef\xcb\x05\x00\xf09\x0c\xe0\x9c\xef\xa6\xb3`\xf5\xae\xa6\xae}\
\x7fx\x9d\xc3\xce\xae\xeb\xea\x84k\xdf\xef\xa0S\x98sn\x05\x8f\x005\xbe\x05\
\x97e\x89u]\x7f\x05\x01\xa0\xeb:m;j\xab\xdeY\x0c%\xb5 \xce\x7fV\xf2\xad\xbf}\
\xa6\x1f\xcf\x96\xd7\xbeL\x1a\x98[\x00\x00\x00\x00IEND\xaeB`\x82\x8f\x88\x8d\
\xc5' )

def getBitmap():
    return wxBitmapFromImage(getImage())

def getImage():
    stream = cStringIO.StringIO(getData())
    return wxImageFromStream(stream)

