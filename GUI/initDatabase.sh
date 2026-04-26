#!/bin/bash

cd PHPserver/dbHandler/
sqlite3 SGData.db "UPDATE infos SET PortConnected = 1 WHERE id=1"
sqlite3 SGData.db "UPDATE infos SET PortConnected = 1 WHERE id=2"
sqlite3 SGData.db "UPDATE infos SET state = 2 WHERE id=1"
sqlite3 SGData.db "UPDATE infos SET state = 2 WHERE id=2"
sqlite3 SGData.db "UPDATE GOOSE SET state = 0 WHERE id=1"
sqlite3 SGData.db "UPDATE GOOSE SET state = 0 WHERE id=4"
sqlite3 SGData.db "UPDATE SV SET state = 0 WHERE id=2"
sqlite3 SGData.db "UPDATE SV SET state = 0 WHERE id=3"
sqlite3 SGData.db "ALTER TABLE infos ADD COLUMN breaker_state INTEGER DEFAULT 2" 2>/dev/null || true
sqlite3 SGData.db "UPDATE infos SET breaker_state = 2"
