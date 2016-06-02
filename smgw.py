import hmac, hashlib, json, socket, threading, logging, time, functools

from halibot import HalModule, Message, Context

log = logging.getLogger(__name__)

class ListenerThread(threading.Thread):
    def __init__(self, module, sockaddr, senders=None, rcps=None, format='<%(snick)s> %(msg)s', msgsize=4096):
        super().__init__()
        self.module = module
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(sockaddr)
        self.sock.setblocking(True)
        self.enabled = True
        self.msgsize = msgsize
        if senders is None:
            senders = {}
        self.senders = senders
        if rcps is None:
            rcps = {}
        self.rcps = rcps
        self.format = format
        self.counter = 0
        self.lastact = 0

    def run(self):
        log.info('Listener on %r starting up...', self.sock.getsockname())
        while True:
            try:
                pkt, src = self.sock.recvfrom(self.msgsize)
                self.pre_throttle()
                if not self.enabled:
                    log.info('From %r: not enabled, ignoring')
                    continue
                try:
                    msg = json.loads(pkt.decode('utf8'))
                except ValueError:
                    log.warning('From %r: couldn\'t parse %r', src, pkt)
                    continue
                log.debug('From %r: %r', src, msg)
                if not (isinstance(msg, dict) and set(['msg', 'auth']) <= set(msg.keys())):
                    log.warning('From %r: protocol broken, can\'t continue', src)
                    continue
                code = msg['auth'].encode('raw_unicode_escape')
                data = msg['msg'].encode('utf8')
                for nick, secret in self.senders.items():
                    hm = hmac.HMAC(secret.encode('raw_unicode_escape'), data, hashlib.sha1)
                    if hm.digest() == code:
                        snick = nick
                        break
                else:
                    log.warning('From %r: couldn\'t authenticate against known senders')
                    continue
                for rcagent, rcset in self.rcps.items():
                    for whom in rcset:
                        ctx = Context(protocol='smgw', whom=whom)
                        msg = Message(body=self.format % {
                            'snick': snick,
                            'src': src,
                            'msg': msg['msg'],
                        }, author=snick, context=ctx)
                        self.module.send_to(msg, [rcagent])
                log.debug('From %r: message send success', src)
                self.post_throttle()
            except Exception:
                log.exception('During processing of message:')

    def pre_throttle(self):
        if self.lastact + self.module.THR_MSG_TIMESPAN < time.time():
            log.debug('Throttle counter reset')
            self.counter = 0
            self.lastact = time.time()
            self.enabled = True
        elif self.counter >= self.module.THR_MSG_THRESHOLD:
            log.debug('Disabled due to throttling')
            self.enabled = False

    def post_throttle(self):
        self.counter += 1
        self.lastact = time.time()

class SMGW(HalModule):
    THR_MSG_THRESHOLD = 3
    THR_MSG_TIMESPAN = 30

    def init(self):
        throt = self.config.get('throttle', {})
        if throt:
            if 'threshold' in throt:
                self.THR_MSG_THRESHOLD = throt['threshold']
            if 'timespan' in throt:
                self.THR_MSG_TIMESPAN = throt['timespan']
        self.listeners = set()
        senders = self.config.get('senders', {})
        msgsize = self.config.get('msgsize', 4096)
        for addr, cfg in self.config.get('insts', {}).items():
            host, _, port = addr.partition(':')
            inst_senders = cfg.get('senders', {})
            inst_senders.update(senders)
            format = cfg.get('format', '<%(snick)s> %(msg)s')
            rcps = cfg.get('rcps', {})
            self.listeners.add(ListenerThread(self, (host, int(port)), inst_senders, rcps, format, msgsize))
        for listener in self.listeners:
            listener.start()

    def receive(self, msg):
        parts = msg.body.split(' ')
        if parts[0].startswith('!'):
            getattr(self, 'cmd_'+parts[0][1:], lambda *args: None)(msg, parts[1:])

    def cmd_smshutup(self, msg, args):
        timeout = 5
        if len(args) > 0:
            try:
                timeout = float(args[0])
            except ValueError:
                pass
        self.reply(msg, body='Sorry, shutting up for %r minutes.'%(timeout,))
        for listener in self.listeners:
            if msg.context.whom in functools.reduce(set.union, listener.rcps.values(), set()):
                listener.counter = self.THR_MSG_THRESHOLD
                listener.lastact = time.time() + (timeout * 60.0) - self.THR_MSG_TIMESPAN
                log.debug('Shutting up listener on %r by !smshutup', listener.sock.getsockname())
            else:
                log.debug('Skipping shutting up listener %r by !smshutup', listener.sock.getsockname())

    def cmd_smhelp(self, msg, args):
        body = 'sm* commands belong to the Simple Message GateWay module. I know these: '
        body += ', '.join(i[4:] for i in dir(self) if i.startswith('cmd_'))
        self.reply(msg, body=body)
