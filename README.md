# SMGW -- Simple Message GateWay

SMGW is:
* The name of a simple JSON-over-UDP protocol, whose reference implementation
  is a...
* Module for [halibot](https://github.com/halibot/halibot) :)

The protocol is, overall, very simple and straightforward; on a client, send a
UDP datagram to a server and port that you agree on, consisting of a JSON
message containing two fields:
* `msg` will be the content of what you want to send, and
* `auth` is your *authenticator*, a value which consists of the HMAC-SHA1 taken
  over the UTF-8 encoding of your message and a shared secret between you and
  the server. The server identifies different clients by possessing different
  shared secrets.

## Halibot Interface

For starters, you will need to add this module to the module instances (by
default, a JSON object of instance names to module configurations). Here's a
configuration example:

```json
"smgw0": {
	"of": "smgw",
	"msgsize": 4096,
	"throttle": {
		"threshold": 3,
		"timespan": 30
	},
	"senders": {
		"VeryTrustedHost": "VTH-HMAC-KEY"
	},
	"insts": {
		":45678": {
			"senders": {
				"TrustedHost1": "TH1-HMAC-KEY"
			},
			"format": "<%(snick)s from %(src)s> %(msg)s",
			"rcps": {
				"irc0": ["#channel1", "#channel2", "bot_maintainer_dude"]
			}
		},
		"127.0.0.1:45679": {
			"rcps": {
				"irc0": ["##private_channel"]
			}
		}
	}
}
```

The schema is as follows, starting inside the configuration object:

* `of` must be `smgw` for Hal to load this module :)
* `msgsize` is the *optional, default 4096* size of the maximum message to try
  and receive. While this is a hard upper limit, note also that the actual MTU
  for UDP is usually quite a bit lower even than this. 
* `throttle` is an *optional* object describing the throttling (anti-flood) measures:
  * `threshold` (*optional, default 3*) describes how many messages may be sent
	in a timespan before throttline occurs
  * `timespan` (*optional, default 30*) describes how many seconds since the
	last sent message to wait before resetting the threshold counter.
* `senders` are the *optional, default empty* globally recognized senders, an
  object whose keys are the names of the sender (as identified by the server)
  and whose corresponding values are the respective HMAC-SHA1 secrets.
* `insts` *optional, default empty* contains all the actual listeners'
  configurations. The key is a `host:port` double (the colon is not optional,
  but the host may be empty--indicating all interfaces) to which to listen,
  while the value is a configuration object:
  * `senders` are *optional, default empty* additional senders for only this
	listener.
  * `format` is a Python `%`-interpolated string that may use the fields:
    * `snick`: The matching sender's name (key of a `senders` object).
	* `src`: The address tuple of the sender.
	* `msg`: The message sent.
  * `rcps` *optional, default empty* is an object whose keys are the names of
	*Halibot agents* to send messages to; each corresponding value is a list of
	values to set `Context.whom` (the target to send to) on that agent. Agents
	are, as usual, specified by name.

To be effective, a minimal configuration should contain at least a `senders`
object (anywhere) and at least one listening `insts` pair, which sends to at
least one `rcps` target.

## Command Line Interface

Included is a small Python script (`cli.py`) whose usage pretty much says
everything:

```
usage: cli.py [-h] [-H HOST] [-p PORT] message

Send a message to a SMGW server.

positional arguments:
  message               Message to send

optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  Host with the SMGW server.
  -p PORT, --port PORT  Port to send to

Note that the shared secret should be passed in the SMGW_SECRET environment
variable.
```
