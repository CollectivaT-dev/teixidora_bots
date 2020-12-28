# Teixidora bots

The repository for doing automated tasks on [teixidora.net](teixidora.net).

## Setup

```
virtualenv -python=python3 venv
source venv/bin/activate
cp teixidora_family.py venv/lib/python3.6/site-packages/pywikibot/families/
```

## Running
Runs via crontab

```
PYWIKIBOT_DIR=<your-dir>
*/5 * * * * flock -n /tmp/tbot.lockfile $PYWIKIBOT_DIR/venv/bin/python3 $PYWIKIBOT_DIR/bot.py -o teixidora -a >> /tmp/corrector.log 2>&1

```

## Tests
To run tests
```
python -m unittest discover -s tests -p "test_*.py" -v
```
