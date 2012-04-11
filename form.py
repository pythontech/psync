def emsg(kv):
    from email.message import Message
    from email.generator import Generator
    from StringIO import StringIO

    m = Message()
    m['Content-type'] = 'multipart/formdata'
    for k,v in kv.items():
        p = Message()
        p.add_header('Content-Disposition', 'form-data', name=k)
        p.set_payload(v)
        m.attach(p)
#print m.as_string()
    fp = StringIO()
    g = Generator(fp)
    g.flatten(m)
    return fp.getvalue()

q = dict(abc='def', ghi='jkl\nmno')

