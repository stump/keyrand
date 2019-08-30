#!/usr/bin/env python3

import bottle
import keyrand
import random

app = bottle.Bottle()

@app.post('/')
def post():
    seed = bottle.request.forms.get('seed')
    if seed == '':
        seed = '0'
    try:
        seed = int(seed)
    except ValueError:
        return get(error='<p class="error">Invalid seed.</p>')
    if seed < 0 or seed >= 4294967296:
        return get(error='<p class="error">Seed out of range.</p>')
    if seed == 0:
        seed = random.randrange(4294967296)
    rom = bottle.request.files.get('rom')
    if not rom:
        return get(error='<p class="error">ROM is required.</p>')
    romimage = bytearray(rom.file.read(1048576))
    if len(romimage) != 1048576 or rom.file.read(1) != b'':
        return get(error='<p class="error">Incorrect ROM size.</p>')
    rando = keyrand.KeyItemRandomizer(seed)
    try:
        rando.apply_randomization(romimage)
    except keyrand.UnrecognizedROM:
        return get(error='<p class="error">Unrecognized ROM image.</p>')
    bottle.response.content_type = 'application/octet-stream'
    bottle.response.set_header('Content-Disposition', 'attachment; filename="randomized-%d.gbc"' % rando.seed)
    return bytes(romimage)

@app.get('/')
def get(error=''):
    return '''
<!DOCTYPE html>
<html>
 <head>
  <title>stump's Pokémon Red/Blue Key Item Randomizer</title>
  <style type="text/css">.error { color: #cc0000; font-weight: bold; }</style>
 </head>
 <body>
  <h1>stump's Pokémon Red/Blue Key Item Randomizer</h1>
  <h2>Things to be aware of</h2>
  <ul>
   <li>Blue's sister will give you her item if you are past the first fight, even if you have not yet delivered Oak's Parcel.</li>
   <li>You can exit Cerulean through the Dig house without visiting Bill first.</li>
   <li>You can enter Silph Co. without visiting Mr. Fuji first. (You still do need to defeat Giovanni in Silph to unlock the Saffron Gym.)</li>
   <li>In exchange for Pokémon Tower no longer being a hard requirement, use of a Poké Doll on the ghost Marowak has been patched.</li>
   <li>The Cut tree between Diglett's Cave and the right gatehouse on Route 2 has been removed.</li>
   <li>The Tea from FireRed/LeafGreen has been added; nothing other than the Tea will allow you into Saffron. (It is randomized like all other key items.)</li>
   <li>Arrow tile movement in Game Corner and the Viridian Gym has been sped up to walking speed.</li>
   <li>Capture requirements for the HM05 and Itemfinder locations have been reduced to 6 and 12, respectively.</li>
   <li>Oak's Aides, the Bike Shop salesman, and the prompts for picking up the fossils will tell you the randomized item.</li>
   <li>All other references to key items in text, outside the immediate act of actually getting the item, will remain unchanged.</li>
   <li>Bike Shop instant text has been patched. No need to worry about invalidating your run when checking what item is there!</li>
  </ul>
  <h2>Randomize a ROM</h2>
  <form method="post" enctype="multipart/form-data">
   %(error)s
   <p><label for="rom">ROM:</label> <input type="file" id="rom" name="rom" /><br />
   Provide a ROM image of English Pokémon Red or Blue. Support for other versions may be added later. ROMs that have already been randomized with the Universal Pokémon Randomizer will work too.</p>
   <p><label for="seed">Seed:</label> <input type="number" id="seed" name="seed" value="0" min="0" max="4294967295" /><br />
   Enter a number from 1 to 4294967295. Enter 0 or leave blank to get a random seed.</p>
   <p><input type="submit" value="Randomize!" /></p>
  </form>
  <p>No ROM images are hosted or stored on this server.</p>
  <p>Please send any questions and feedback (including bug reports) to <a href="https://stump.io/discord">stump's Discord</a>.</p>
 </body>
</html>
''' % {'error': error}

if __name__ == '__main__':
    app.run()
