#!/usr/bin/env bash
cd /home/ultron/protocol_pulse || exit 1
export PATH="/usr/bin:/usr/local/bin:$PATH"
/usr/bin/python3 -m services.satomi_brief_generator
