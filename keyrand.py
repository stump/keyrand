#!/usr/bin/env python3

import binascii
import json
import random
import sys

KEY_ITEMS = ['OAK\'s PARCEL',
             'TOWN MAP',
             'HM05',
             'OLD AMBER',
             'HELIX FOSSIL',
             'DOME FOSSIL',
             'BICYCLE',
             'S.S. TICKET',
             'OLD ROD',
             'BIKE VOUCHER',
             'HM01',
             'ITEMFINDER',
             'POKé FLUTE',
             'COIN CASE',
             'LIFT KEY',
             'SILPH SCOPE',
             'SUPER ROD',
             'GOOD ROD',
             'GOLD TEETH',
             'HM03',
             'HM04',
             'HM02',
             'CARD KEY',
             'SECRET KEY']

KEY_ITEM_IDS = {
  'OAK\'s PARCEL': 0x46,
  'TOWN MAP': 0x05,
  'HM05': 0xc8,
  'OLD AMBER': 0x1f,
  'HELIX FOSSIL': 0x2a,
  'DOME FOSSIL': 0x29,
  'BICYCLE': 0x06,
  'S.S. TICKET': 0x3f,
  'OLD ROD': 0x4c,
  'BIKE VOUCHER': 0x2d,
  'HM01': 0xc4,
  'ITEMFINDER': 0x47,
  'POKé FLUTE': 0x49,
  'COIN CASE': 0x45,
  'LIFT KEY': 0x4a,
  'SILPH SCOPE': 0x48,
  'SUPER ROD': 0x4e,
  'GOOD ROD': 0x4d,
  'GOLD TEETH': 0x40,
  'HM03': 0xc6,
  'HM04': 0xc7,
  'HM02': 0xc5,
  'CARD KEY': 0x30,
  'SECRET KEY': 0x2b,
}

# Prevent items from requiring themselves to get to them.
# Oak's Parcel is special-cased as you only have access to two
# key item slots by the time you need it.
HARD_DEPENDENCIES = {
  'SECRET KEY': {'HM03', 'POKé FLUTE'},
  'HM04': {'GOLD TEETH', 'POKé FLUTE'},
  'GOLD TEETH': {'POKé FLUTE'},
  'HM03': {'POKé FLUTE'},
  'GOOD ROD': {'POKé FLUTE'},
  'HM02': {'HM01'},
  'SILPH SCOPE': {'LIFT KEY'},
  'SUPER ROD': {'POKé FLUTE'},
  'HM01': {'S.S. TICKET'},
  'OLD AMBER': {'HM01'},
  'BICYCLE': {'BIKE VOUCHER'},
}

# These are needed to complete the game.
# Again, Oak's Parcel is special-cased.
REQUIRED_TO_COMPLETE_GAME = {'HM01', 'HM03', 'HM04', 'POKé FLUTE', 'CARD KEY', 'SECRET KEY'}


class UnrecognizedROM(Exception):
    pass


class KeyItemRandomizer(object):

    def __init__(self, seed):
        self.random = random.Random()
        self.random.seed(seed, version=2)
        self.seed = seed

        initial_order = KEY_ITEMS[:]
        self.random.shuffle(initial_order)
        self.mapping = dict(zip(KEY_ITEMS, initial_order))

        self.accessible_slots = set()

        self.generate_randomization()

    def reverse_mapping(self):
        return {v: k for k, v in self.mapping.items()}

    def dump_mapping(self, stream=sys.stderr):
        import pprint
        pprint.pprint(self.mapping, stream=stream)

    def item_is_accessible(self, item):
        return any(self.mapping[i] == item for i in self.accessible_slots)

    def swap_with_random_accessible_item(self, item):
        k1, k2 = self.random.choice(sorted(self.accessible_slots)), self.reverse_mapping()[item]
        self.mapping[k1], self.mapping[k2] = self.mapping[k2], self.mapping[k1]

    def generate_randomization(self):
        # Take the initial order and switch things around until we get an arrangement that's possible.

        while True:
            # Ensure no item hard-requires itself to reach.
            swaps_made = False
            for slot, excluded_items in sorted(HARD_DEPENDENCIES.items()):
                if self.mapping[slot] in excluded_items:
                    self.accessible_slots = set(self.mapping.keys()) - {slot}
                    self.swap_with_random_accessible_item(self.mapping[slot])
                    swaps_made = True
            if swaps_made:
                continue

            # Ensure we can get past Viridian.
            self.accessible_slots = {'OAK\'s PARCEL', 'TOWN MAP'}
            if not self.item_is_accessible('OAK\'s PARCEL'):
                self.swap_with_random_accessible_item('OAK\'s PARCEL')
                continue

            # Once we're in the Cerulean/Vermilion/Route 2 trap,
            # do an expanding search for all items required to
            # complete the game.
            # Don't consider Itemfinder accessible until either
            # Poké Flute or HM01 have been found. 30 Pokémon
            # owned is a little steep if you're stuck in that
            # trap. (10 for HM05 is OK though.)
            #
            # HM05 is here because we remove the Cut tree that
            # blocks it. This is to potentially allow 10 Pokémon
            # to be required to escape the trap. (Also I forgot
            # about that Cut tree when making the initial logic,
            # there's precedent for removing it in the fact that
            # there's no such obstacle in FireRed/LeafGreen, we
            # were thinking at one point of backporting another
            # FR/LG change (namely the Tea) but decided not to,
            # and I just like the idea of possibly needing 10
            # (but definitely not 30!) Pokémon to get anywhere
            # other than Cerulean and Vermilion.
            #
            # (Fun fact: In the worst case [nothing but starter,
            # no rods, HM01 or Flute at Itemfinder and the other
            # not accessible without it], it is possible to get
            # to exactly 30 owned if you catch and fully evolve
            # everything you have access to [other than stones
            # and trades], do the in-game trades you have access
            # to that you can do with accessible Pokémon, and
            # fully evolve your starter. [This applies whether
            # or not that one Cut tree on Route 2 is removed.]
            # It would be utterly sadistic to force this upon
            # players, though, so we consider that slot to
            # depend on anything at all that would open up more
            # of the game.)
            self.accessible_slots = {'S.S. TICKET', 'OLD ROD', 'BIKE VOUCHER', 'HM05'}
            while not all(self.item_is_accessible(item) for item in REQUIRED_TO_COMPLETE_GAME):
                potential_swaps = set()

                # Cut (requiring the Cascadebadge, which you always have access to)
                # allows traversing Rock Tunnel (and thus Lavender/Celadon/Saffron)
                # and returning to Pallet/Viridian/Pewter via Diglett's Cave and Route 2.
                #
                # We do not consider Silph Scope a dependency of the Poké Flute slot.
                # (Should we? We can easily patch the oversight in question.)
                new_slots = {'ITEMFINDER', 'OAK\'s PARCEL', 'TOWN MAP', 'OLD AMBER', 'POKé FLUTE', 'LIFT KEY', 'HM02', 'COIN CASE', 'CARD KEY'}
                if new_slots - self.accessible_slots:
                    if self.item_is_accessible('HM01'):
                        self.accessible_slots.update(new_slots)
                        continue
                    else:
                        potential_swaps.add('HM01')

                # Bike Voucher gives the Bicycle slot.
                if 'BICYCLE' not in self.accessible_slots:
                    if self.item_is_accessible('BIKE VOUCHER'):
                        self.accessible_slots.add('BICYCLE')
                        continue
                    else:
                        potential_swaps.add('BIKE VOUCHER')

                # S.S. Ticket gives the HM01 slot.
                if 'HM01' not in self.accessible_slots:
                    if self.item_is_accessible('S.S. TICKET'):
                        self.accessible_slots.add('HM01')
                        continue
                    else:
                        potential_swaps.add('S.S. TICKET')

                # Poké Flute allows access to Fuchsia by waking either Snorlax.
                # It also opens up Lavender/Celadon/Saffron without Cut by waking
                # the Route 12 Snorlax.
                #
                # We do not consider Silph Scope a dependency of the Poké Flute slot.
                # (Should we? We can easily patch the oversight in question.)
                new_slots = {'ITEMFINDER', 'POKé FLUTE', 'SUPER ROD', 'LIFT KEY', 'COIN CASE', 'GOOD ROD', 'HM03', 'GOLD TEETH', 'CARD KEY'}
                if new_slots - self.accessible_slots:
                    if self.item_is_accessible('POKé FLUTE'):
                        self.accessible_slots.update(new_slots)
                        continue
                    else:
                        potential_swaps.add('POKé FLUTE')

                # Lift Key gives the Silph Scope slot, but Celadon must be reachable.
                if 'SILPH SCOPE' not in self.accessible_slots:
                    if (self.item_is_accessible('HM01') or self.item_is_accessible('POKé FLUTE')) and self.item_is_accessible('LIFT KEY'):
                        self.accessible_slots.add('SILPH SCOPE')
                        continue
                    else:
                        potential_swaps.update({'HM01', 'POKé FLUTE', 'LIFT KEY'})

                # Gold Teeth gives the HM04 slot, but Fuchsia must be reachable.
                # We do not need to consider access to Fuchsia via Surf from
                # Pallet/Cinnabar because Surf requires the Soulbadge, which is
                # in Fuchsia.
                if 'HM04' not in self.accessible_slots:
                    if self.item_is_accessible('POKé FLUTE') and self.item_is_accessible('GOLD TEETH'):
                        self.accessible_slots.add('HM04')
                        continue
                    else:
                        potential_swaps.update({'POKé FLUTE', 'GOLD TEETH'})

                # Surf allows access to Cinnabar and Pallet/Viridian/Pewter.
                # It requires the Soulbadge, so Fuchsia must be reachable.
                new_slots = {'OAK\'s PARCEL', 'TOWN MAP', 'SECRET KEY'}
                if new_slots - self.accessible_slots:
                    if self.item_is_accessible('POKé FLUTE') and self.item_is_accessible('HM03'):
                        self.accessible_slots.update(new_slots)
                        continue
                    else:
                        potential_swaps.update({'POKé FLUTE', 'HM03'})

                # We do not need to consider access to Pallet/Viridian/Pewter via
                # Fly because Fly requires the Thunderbadge, which requires the
                # use of Cut or Surf, either of which also allow access to Pallet/
                # Viridian/Pewter.

                # Swap some item that will open up more key item slots into
                # a key item slot that is accessible in the current arrangement.
                item_to_swap = self.random.choice([item for item in sorted(REQUIRED_TO_COMPLETE_GAME | potential_swaps) if not self.item_is_accessible(item)])
                self.swap_with_random_accessible_item(item_to_swap)
                swaps_made = True
                continue

            # If the reachability analysis didn't result in any swaps,
            # we're finished and have a completable permutation of items.
            if not swaps_made:
                break

    def apply_randomization(self, rom):
        # The memoryview here is a check against accidentally resizing the ROM when
        # using slice assignment to apply the patches if what was passed is a bytearray.
        rom = memoryview(rom)

        def replace(rom, addr, oldhex, newhex):
            oldbin = binascii.unhexlify(oldhex)
            newbin = binascii.unhexlify(newhex)
            assert len(oldbin) == len(newbin)
            if rom[addr:addr+len(oldbin)] != oldbin:
                raise UnrecognizedROM(addr)
            rom[addr:addr+len(newbin)] = newbin

        def replace_item(rom, addr, name):
            if rom[addr] != KEY_ITEM_IDS[name]:
                raise UnrecognizedROM(addr)
            rom[addr] = KEY_ITEM_IDS[self.mapping[name]]

        # These hex strings are from applying a patch in the patches/ directory to
        # pokered, rebuilding, then checking for different bytes.
        # I did these by running "cmp -l", then slicing out the bytes in the indicated
        # locations in the ROMs by hand in a Python REPL and copying them here.
        # (Remember that cmp, for some incomprehensible reason, starts counting at 1!)
        # Patches for automating this are welcome.
        #
        # Useful one-liner:
        # cmp -l vanillared.gbc pokered.gbc | python3 -c 'for line in __import__("sys").stdin: a, b, c = line.split(); print(hex(int(a)-1), hex(int(b,8)), hex(int(c,8)))'

        # Bicycle slot
        #At 0x1d754, fc (jump fixup)
        replace(rom, 0x1d754, 'f5', 'fc')
        #At 0x1d75c, 2c (jump fixup)
        replace(rom, 0x1d75c, '2f', '2c')
        #At 0x1d765, new item
        replace_item(rom, 0x1d765, 'BICYCLE')
        #At 0x1d783, 78 (jump fixup)
        replace(rom, 0x1d783, '71', '78')
        #At 0x1d787, 18f6211058cd493cafea26ccea2acc3e03ea29cc3e01ea28ccea25cc3cea24cc2130d7cbf621a0c3010f04cd2219cd29243e06ea1ed1cdcf2f21cac3116dcdcd551911ff57cd551921e4c3110758cd5519211558cd493ccdbe3a2130d7cbb6cb4f200cfa26cca72006211a58cd493c212a58cd493cc3d724 (put correct item in menu when you don't have voucher, and patch instant text)
        replace(rom, 0x1d787, 'cd493c1869211058cd493cafea26ccea2acc3e03ea29cc3e01ea28cc3e02ea24cc3e01ea25cc2130d7cbf621a0c306040e0fcd2219cd292421cac311f857cd551921e4c3110758cd5519211558cd493ccdbe3acb4f20112130d7cbb6fa26cca72006211a58cd493c212a58cd493cc3d72481888298828b84', '18f6211058cd493cafea26ccea2acc3e03ea29cc3e01ea28ccea25cc3cea24cc2130d7cbf621a0c3010f04cd2219cd29243e06ea1ed1cdcf2f21cac3116dcdcd551911ff57cd551921e4c3110758cd5519211558cd493ccdbe3a2130d7cbb6cb4f200cfa26cca72006211a58cd493c212a58cd493cc3d724')
        #At 0x1d7b9, new item
        replace_item(rom, 0x1d7b9, 'BICYCLE')
        #At 0x98ed4, 50014bcf00e8505000 (so text from wcf4b is used)
        replace(rom, 0x98ed4, 'a07f81888298828b84', '50014bcf00e8505000')

        # Bike Voucher slot
        #At 0x59b78, c9 (give item even if bike or voucher already in bag)
        replace(rom, 0x59b78, 'c0', 'c9')
        #At 0x59c39, new item
        replace_item(rom, 0x59c39, 'BIKE VOUCHER')
        #At 0x9a83a, 50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0x9a83a, 'a07f50014bcf00e750', '50014bcf00e7505000')

        # Card Key slot
        #At 0x1a0e7, new item
        replace_item(rom, 0x1a0e7, 'CARD KEY')

        # Coin Case slot
        #At 0x49183, new item
        replace_item(rom, 0x49183, 'COIN CASE')
        #At 0x9e086, 50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0x9e086, 'a07f50014bcf00e750', '50014bcf00e7505000')

        # Dome Fossil slot
        #At 0x49e40, 24 (pointer to adjusted text)
        replace(rom, 0x49e40, '29', '24')
        #At 0x49eef, 3e29cd195f211f5fcd493ccdec35fa26cca7205e010129cd2e3ed2765fcd695f21f6d7cbf63e6dc3515fea1ed1c3cf2f175e492050083e01ea3ccc3e2acd195f (put correct item in text when confirming picking up items)
        replace(rom, 0x49eef, '21245fcd493ccdec35fa26cca72023010129cd2e3ed2765fcd695f3e6dea4dcc3e11cd6d3e21f6d7cbf63e04ea07d6ea39dac3d724175e492050083e01ea3ccc', '3e29cd195f211f5fcd493ccdec35fa26cca7205e010129cd2e3ed2765fcd695f21f6d7cbf63e6dc3515fea1ed1c3cf2f175e492050083e01ea3ccc3e2acd195f')
        #At 0x49ef0, new item
        replace_item(rom, 0x49ef0, 'DOME FOSSIL')
        #At 0x49f05, new item
        replace_item(rom, 0x49f05, 'DOME FOSSIL')
        #At 0x49f4a, 21f6d7cbfe3e6eea4dcc3e11cd6d3e (put correct item in text when confirming picking up items)
        replace(rom, 0x49f4a, '3e6eea4dcc3e11cd6d3e21f6d7cbfe', '21f6d7cbfe3e6eea4dcc3e11cd6d3e')
        #At 0x80967, 4f50016dcd00e65700 (remove "the" before item name in text)
        replace(rom, 0x80967, '7fb3a7a44f838e8c84', '4f50016dcd00e65700')
        #At 0x8099b, 4f50014bcf00e7505000 (remove "the" before item name in text)
        replace(rom, 0x8099b, '7fb3a7a44f50014bcf00', '4f50014bcf00e7505000')

        # Gold Teeth slot
        #At 0x4a227, new item
        replace_item(rom, 0x4a227, 'GOLD TEETH')

        # Good Rod slot
        #At 0x5619a, new item
        replace_item(rom, 0x5619a, 'GOOD ROD')
        #At 0xa072d, 50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0xa072d, 'a07f50014bcf00e750', '50014bcf00e7505000')

        # Helix Fossil slot
        # Fixups from Dome Fossil
        #At 0x49f2b, new item
        replace_item(rom, 0x49f2b, 'HELIX FOSSIL')
        #At 0x49f40, new item
        replace_item(rom, 0x49f40, 'HELIX FOSSIL')
        #At 0x80982, 4f50016dcd00e65700 (remove "the" before item name in text)
        replace(rom, 0x80982, '7fb3a7a44f87848b88', '4f50016dcd00e65700')

        # HM01 slot
        #At 0x618c3, new item
        replace_item(rom, 0x618c3, 'HM01')

        # HM02 slot
        #At 0x1e612, new item
        replace_item(rom, 0x1e612, 'HM02')
        #At 0x1e631, 9954 (repoint text to S.S. Ticket text, which uses text from wcf4b)
        replace(rom, 0x1e631, '664e', '9954')

        # HM03 slot
        #At 0x4a32c, new item
        replace_item(rom, 0x4a32c, 'HM03')

        # HM04 slot
        #At 0x75111, new item
        try:
            replace_item(rom, 0x75111, 'HM04')
        except UnrecognizedROM:
            # Maybe it's Blue.
            replace_item(rom, 0x75112, 'HM04')

        # HM05 slot
        #At 0x540f3, 6d (remove Cut tree in the way)
        replace(rom, 0x540f3, '32', '6d')
        #At 0x5d5e4, 06 (lower capture requirement to 6)
        replace(rom, 0x5d5e4, '0a', '06')
        #At 0x5d5e8, new item
        replace_item(rom, 0x5d5e8, 'HM05')
        #At 0x801a3, 5550015bcc00e7500505 (remove "an" before item name in aide script text)
        replace(rom, 0x801a3, '7fa0ad5550015bcc00e7', '5550015bcc00e7500500')
        #At 0x80244, 5550015bcc00e85700 (remove "the" before item name in aide script text)
        replace(rom, 0x80244, '7fb3a7a45550015bcc', '5550015bcc00e85700')
        #At 0x802df, 4f50015bcc00e7505000 (remove "the" before item name in aide script text)
        replace(rom, 0x802df, '7fb3a7a44f50015bcc00', '4f50015bcc00e7505000')
        #At 0x80311, 5550015bcc00e85700 (remove "the" before item name in aide script text)
        replace(rom, 0x80311, '7fb3a7a45550015bcc', '5550015bcc00e85700')
        # TODO: Pokédex evaluation

        # Itemfinder slot
        #At 0x49474, 0c (lower capture requirement to 12)
        replace(rom, 0x49474, '1e', '0c')
        #At 0x49478, new item
        replace_item(rom, 0x49478, 'ITEMFINDER')
        # Aide script fixups from HM05.
        # TODO: Pokédex evaluation

        # Lift Key slot
        #At 0x45643, new item
        replace_item(rom, 0x45643, 'LIFT KEY')

        # Oak's Parcel slot
        #At 0x1d46e, 000000 (delay shuffling of mart text pointers)
        replace(rom, 0x1d46e, 'cd7d54', '000000')
        #At 0x1d499, 7d (delay shuffling of mart text pointers)
        replace(rom, 0x1d499, 'df', '7d')
        #At 0x1d4c8, 010146cd2e3e3e05e08ccd2029 (so right text is in wcf4b)
        replace(rom, 0x1d4c8, '3e05e08ccd2029010146cd2e3e', '010146cd2e3e3e05e08ccd2029')
        #At 0x1d4ca, new item
        replace_item(rom, 0x1d4ca, 'OAK\'s PARCEL')
        #At 0x95cc7, 50014bcf00e7505000 (so text from wcf4b is used)
        replace(rom, 0x95cc7, '8e808abd7f8f809182', '50014bcf00e7505000')
        # TODO: Add error check for a full bag since this is no longer a forced pickup.

        # Old Amber slot
        #At 0x5c266, new item
        replace_item(rom, 0x5c266, 'OLD AMBER')
        #At 0x9679c, 50014bcf00e7505000 (so text from wcf4b is used)
        replace(rom, 0x9679c, '8e8b837f808c818491', '50014bcf00e7505000')

        # Old Rod slot
        #At 0x5608e, new item
        replace_item(rom, 0x5608e, 'OLD ROD')
        #At 0x9c599, 50014bcf00e7505000 (remove "an" before item name in text)
        replace(rom, 0x9c599, 'a0ad7f50014bcf00e7', '50014bcf00e7505000')

        # Poké Flute slot
        #At 0x1d928, new item
        replace_item(rom, 0x1d928, 'POKé FLUTE')
        #At 0x9a007, 50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0x9a007, 'a07f50014bcf00e750', '50014bcf00e7505000')

        # S.S. Ticket slot
        #At 0x1e884, new item
        replace_item(rom, 0x1e884, 'S.S. TICKET')
        #At 0x8d4a5, 50014bcf00e7505000 (remove "an" before item name in text)
        replace(rom, 0x8d4a5, 'a0ad7f50014bcf00e7', '50014bcf00e7505000')
        # Make Bill not be required by changing the initial state of the Cerulean guards.
        #At 0x0cb01, 15 (show the stepped-aside guard)
        replace(rom, 0x0cb01, '11', '15')
        #At 0x0cb07, 11 (hide the blocking guard)
        replace(rom, 0x0cb07, '15', '11')

        # Secret Key slot
        #At 0x524d8, new item
        replace_item(rom, 0x524d8, 'SECRET KEY')

        # Silph Scope slot
        #At 0x4563c, new item
        replace_item(rom, 0x4563c, 'SILPH SCOPE')

        # Super Rod slot
        #At 0x5649d, new item
        replace_item(rom, 0x5649d, 'SUPER ROD')
        #At 0x8ca45, 50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0x8ca45, 'a07f50014bcf00e750', '50014bcf00e7505000')

        # Town Map slot
        #At 0x19b69, 5f (give you the item after just fighting Rival I, not after delivering parcel)
        replace(rom, 0x19b69, '6f', '5f')
        #At 0x19b7c, new item
        replace_item(rom, 0x19b7c, 'TOWN MAP')
        #At 0x94ca2, 4f50014bcf00e7505000 (remove "a" before item name in text)
        replace(rom, 0x94ca2, '7fa04f50014bcf00e750', '4f50014bcf00e7505000')

        # Add randomizer info to the main menu screen.
        #At 0x05b20, 497c (reroute the menu's clear-screen call to new code)
        replace(rom, 0x05b20, '0f19', '497c')
        #At 0x05ba8, 257d (reroute the menu's options screen to new code)
        replace(rom, 0x05ba8, '8a5e', '257d')
        #At 0x07c49, cd0f193effea2fd43e03ea67d33e19cd6d3ecd6100cde809cd7b0021b0c311bd7ccd55192192c411c27ccd55192154c411d37ccd55192168c411e77ccd551921bec411fb7ccd551921d4c411057dcd551921e6c4110f7dcd551921fcc4111a7dcd551921cec43e02223c7721e2c43e12223c77c9b5f6e8f85092a4a4a39c7ffaf8fffafffcfdf8fffb50b2b3b4acafbd7f86a4ada4b1a0b3a8aead7ff7508aa4b87f88b3a4ac7f91a0ada3aeaca8b9a4b150b2b3b4acafe8a8aef350a8b3a4acb1a0ada3ae50b3b6a8b3a2a7e8b3b5f350b2b3b4acafa3aeb3a8ae50cd0f19c38a5e (new code)
        replace(rom, 0x07c49, '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000', 'cd0f193effea2fd43e03ea67d33e19cd6d3ecd6100cde809cd7b0021b0c311bd7ccd55192192c411c27ccd55192154c411d37ccd55192168c411e77ccd551921bec411fb7ccd551921d4c411057dcd551921e6c4110f7dcd551921fcc4111a7dcd551921cec43e02223c7721e2c43e12223c77c9b5f6e8f85092a4a4a39c7ffaf8fffafffcfdf8fffb50b2b3b4acafbd7f86a4ada4b1a0b3a8aead7ff7508aa4b87f88b3a4ac7f91a0ada3aeaca8b9a4b150b2b3b4acafe8a8aef350a8b3a4acb1a0ada3ae50b3b6a8b3a2a7e8b3b5f350b2b3b4acafa3aeb3a8ae50cd0f19c38a5e')

        # Patch the seed into the new main menu screen info.
        seedbytes = str(self.seed).rjust(10).translate({
          ord(' '): 0x7f,
          ord('0'): 0xf6,
          ord('1'): 0xf7,
          ord('2'): 0xf8,
          ord('3'): 0xf9,
          ord('4'): 0xfa,
          ord('5'): 0xfb,
          ord('6'): 0xfc,
          ord('7'): 0xfd,
          ord('8'): 0xfe,
          ord('9'): 0xff,
        }).encode('iso-8859-1')
        rom[0x07cc8:0x07cd2] = seedbytes

        # Fix the checksum.
        rom[0x0014e:0x00150] = b'\0\0'
        checksum = sum(rom) & 0xffff
        rom[0x0014e] = checksum >> 8
        rom[0x0014f] = checksum & 0xff



if __name__ == '__main__':
    if len(sys.argv) == 2:
        seed = int(sys.argv[1])
        if seed < 0 or seed >= 4294967296:
            print('Seed is out of range.', file=sys.stderr)
            sys.exit(1)
    else:
        seed = random.randrange(4294967296)
    print('Seed: {}'.format(seed), file=sys.stderr)
    rando = KeyItemRandomizer(seed)

    rando.dump_mapping()

    if sys.stdin.isatty():
        print('Pass a ROM image on stdin to get the randomized ROM on stdout.', file=sys.stderr)
        sys.exit()

    rom = bytearray(sys.stdin.buffer.read())
    if len(rom) != 1048576:
        print('ROM image is not of expected length.', file=sys.stderr)
        print('Instead, here is the randomization in JSON on stdout.', file=sys.stderr)
        print(json.dumps(rando.mapping))
        sys.exit(1)

    if sys.stdout.isatty():
        print('Refusing to write ROM image to terminal.', file=sys.stderr)
        sys.exit(1)

    rando.apply_randomization(rom)
    sys.stdout.buffer.write(rom)
