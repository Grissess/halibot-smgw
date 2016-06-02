import socket, hashlib, hmac, json, argparse, os

parser = argparse.ArgumentParser(description='Send a message to a SMGW server.', epilog='Note that the shared secret should be passed in the SMGW_SECRET environment variable.')
parser.add_argument('-H', '--host', dest='host', default='127.0.0.1', help='Host with the SMGW server.')
parser.add_argument('-p', '--port', dest='port', type=int, default=45678, help='Port to send to')
parser.add_argument('message', help='Message to send')

args = parser.parse_args()
authcode = hmac.HMAC(os.environb[b'SMGW_SECRET'], args.message.encode('utf8'), hashlib.sha1).digest()
pkt = json.dumps({'msg': args.message, 'auth': authcode.decode('raw_unicode_escape')})
so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
so.sendto(pkt.encode('utf8'), (args.host, args.port))
