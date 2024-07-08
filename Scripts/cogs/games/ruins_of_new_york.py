import logging

logger = logging.getLogger(__name__)

class Game:
    def __init__(self):
        self.locations = {
            "ruins": {
                "description": "You stand amidst the RUINS OF NEWYORK: collapsed buildings, burned-out vehicles and broken streets surround you. There is a rusting bicycle here. You see a store here with cracked windows and a door that's still on its hinges. The street is mostly clear to the north.",
                "exits": {"enter store": "store", "north": "tunnel_entrance"},
                "items": ["bicycle"]
            },
            "store": {
                "description": "The store stocks mostly debris and detritus. Only a few toppled shelves remain.",
                "exits": {"out": "ruins"},
                "items": ["cheez-ees", "book"]
            },
            "tunnel_entrance": {
                "description": "You arrive at the mouth of a dark tunnel that threatens to swallow you whole.",
                "exits": {"enter dark tunnel": "dark_tunnel", "south": "ruins"},
                "items": []
            },
            "dark_tunnel": {
                "description": "After traveling through the tunnel for what seems like forever, several hunched humanoid figures scramble from the darkness—you find yourself surrounded.",
                "exits": {"east": "platform", "west": "tunnel_entrance"},
                "items": [],
                "rat_people": True
            },
            "platform": {
                "description": "You are on a platform. There is a vending machine here. A stairway leads back up to the surface. A wrecked bike lies on the floor of the tunnel below you.",
                "exits": {"up": "burning_canal"},
                "items": ["wrecked_bike"],
                "vending_machine": True
            },
            "burning_canal": {
                "description": "The water in the canal below the bridge is ruined and poisonous; flaming oil slicks burn on its surface. A stairway leads back down to the underworld. The bridge crosses over the canal to the south.",
                "exits": {"south": "market", "down": "platform"},
                "items": []
            },
            "market": {
                "description": "In the distance you see a gathering of people attending an open-air market. Beyond the market is the entrance to a scrapyard. The bridge is back whence you came.",
                "exits": {"enter scrapyard": "scrapyard", "north": "burning_canal"},
                "items": [],
                "mutant_leader": True
            },
            "scrapyard": {
                "description": "You're surrounded by carefully sorted and stacked piles of junk. Metal cans, glass bottles, plastic containers, bales of cardboard, discarded electronics, and junked cars. There is an unsorted junk pile here. You see a concrete bunker.",
                "exits": {"out": "market", "enter bunker": "bunker"},
                "items": ["motor", "car_battery", "drive_belt", "jumper_cables", "wires"]
            },
            "bunker": {
                "description": "The bunker seems like a shrine to the Old World: posters of long-dead celebrities are on the walls and board games, plastic figurines and brightly colored boxes of cereal line the shelves. On a desk in the corner is a dusty old computer. A toolbox is here.",
                "exits": {"out": "scrapyard"},
                "items": ["toolbox"],
                "computer": True,
                "power_inverter": True
            }
        }
        self.current_location = "ruins"
        self.inventory = []
        self.score = 0
        self.riding_bicycle = False
        self.generator_built = False
        self.computer_powered = False
        self.floppy_disk = False
        self.rat_people_distracted = False
        self.energy_drink_opened = False
        self.is_game_over = False
        logger.info("Game initialized")
        logger.debug(f"Initial location: {self.current_location}")
        logger.debug(f"All locations: {list(self.locations.keys())}")

    def play(self):
        output = []
        output.append("Welcome to the Ruins of New York!")
        output.append("In this post-apocalyptic adventure, you'll navigate through dangerous terrain,")
        output.append("solve puzzles, and uncover the secrets of the old world.")
        output.append("Type 'help' at any time for a list of commands.")
        output.append(self.look())
        return "\n".join(output)

    def process_command(self, command):
        logger.info(f"Processing command: {command}")
        command = command.lower().split()
        if not command:
            return "Please enter a command."

        action = command[0]
        logger.debug(f"Action: {action}")

        if action in ["go", "move", "walk", "run", "exit", "leave", "enter"]:
            direction = " ".join(command[1:]) if len(command) > 1 else ""
            return self.go(direction)
        elif action in self.locations[self.current_location]["exits"]:
            return self.go(action)
        elif action == "look":
            return self.look()
        elif action == "inventory":
            return self.show_inventory()
        elif action == "take":
            if len(command) > 1:
                return self.take(command[1])
            else:
                return "Take what?"
        elif action == "examine":
            if len(command) > 1:
                return self.examine(" ".join(command[1:]))
            else:
                return "Examine what?"
        elif action == "ride":
            if len(command) > 1 and command[1] == "bicycle":
                return self.ride_bicycle()
            else:
                return "Ride what?"
        elif action == "read":
            if len(command) > 1 and command[1] == "book":
                return self.read_book()
            else:
                return "Read what?"
        elif action in ["shake", "punch", "kick"]:
            if len(command) > 1 and command[1] == "machine":
                return self.interact_vending_machine()
            else:
                return f"{action.capitalize()} what?"
        elif action == "open":
            if len(command) > 1 and command[1] == "can":
                return self.open_can()
            else:
                return "Open what?"
        elif action == "drink":
            if len(command) > 1 and command[1] == "can":
                return self.drink_can()
            else:
                return "Drink what?"
        elif action == "talk":
            if len(command) > 2 and command[1] == "to":
                return self.talk_to(" ".join(command[2:]))
            else:
                return "Talk to whom?"
        elif action == "trade":
            return self.trade()
        elif action == "build":
            if len(command) > 1 and command[1] == "generator":
                return self.build_generator()
            else:
                return "Build what?"
        elif action == "attach":
            if len(command) > 3 and command[2] == "to":
                return self.attach(command[1], " ".join(command[3:]))
            else:
                return "Attach what to what?"
        elif action == "pedal":
            if len(command) > 1 and command[1] == "bike":
                return self.pedal_bike()
            else:
                return "Pedal what?"
        elif action == "turn":
            if len(command) > 2 and command[1] == "on" and command[2] == "computer":
                return self.turn_on_computer()
            else:
                return "Turn on what?"
        elif action == "insert":
            if len(command) > 1 and command[1] == "floppy":
                return self.insert_floppy()
            else:
                return "Insert what?"
        elif action == "consult":
            if len(command) > 3 and command[1] == "book" and command[2] == "about":
                return self.consult_book(command[3])
            else:
                return "Consult what about what?"
        elif action == "help":
            return self.get_help()
        elif action == "quit":
            self.is_game_over = True
            return f"You have quit the game. Your final score: {self.score}"
        else:
            return "I don't understand that command. Type 'help' for a list of commands."

    def go(self, direction):
        logger.info(f"Go method called with direction: {direction}")
        loc = self.locations[self.current_location]
        logger.debug(f"Current location: {self.current_location}")
        logger.debug(f"Available exits: {loc['exits']}")
        
        direction = direction.lower()
        
        # Check for exact match first
        if direction in loc["exits"]:
            new_location = loc["exits"][direction]
            logger.debug(f"Exact match found. New location: {new_location}")
        else:
            # If no exact match, look for partial matches
            matching_exits = [exit for exit in loc["exits"].keys() if direction in exit.lower()]
            logger.debug(f"Matching exits: {matching_exits}")
            if matching_exits:
                # If there's only one match, use it
                if len(matching_exits) == 1:
                    new_location = loc["exits"][matching_exits[0]]
                    logger.debug(f"Single partial match found. New location: {new_location}")
                else:
                    # If there are multiple matches, check if one contains all words
                    direction_words = direction.split()
                    full_matches = [exit for exit in matching_exits if all(word in exit.lower() for word in direction_words)]
                    if full_matches:
                        new_location = loc["exits"][full_matches[0]]
                        logger.debug(f"Full partial match found. New location: {new_location}")
                    else:
                        logger.warning(f"Multiple partial matches found, but no full match for: {direction}")
                        return f"Did you mean one of these: {', '.join(matching_exits)}?"
            else:
                logger.warning(f"No matching exit found for direction: {direction}")
                return f"You can't go '{direction}'. Valid exits are: {', '.join(loc['exits'].keys())}"
        
        if new_location == "dark_tunnel" and not self.riding_bicycle and not self.rat_people_distracted:
            logger.info("Prevented from entering dark tunnel due to danger")
            return "The tunnel looks dangerous. You might need a quick way to escape if things go wrong."
        
        self.current_location = new_location
        logger.info(f"Moved to new location: {self.current_location}")
        return self.look()

    def look(self):
        logger.info(f"Look method called. Current location: {self.current_location}")
        loc = self.locations[self.current_location]
        output = f"You are in the {self.current_location}.\n"
        output += loc["description"] + "\n"
        if loc["items"]:
            output += "You see: " + ", ".join(loc["items"]) + "\n"
        output += "Exits: " + ", ".join(loc["exits"].keys())
        logger.debug(f"Look output: {output}")
        return output

    def show_inventory(self):
        if self.inventory:
            return "You are carrying: " + ", ".join(self.inventory)
        else:
            return "Your inventory is empty."

    def take(self, item):
        loc = self.locations[self.current_location]
        if item in loc["items"]:
            loc["items"].remove(item)
            self.inventory.append(item)
            output = f"You picked up the {item}."
            if item == "cheez-ees":
                self.score += 5
                output += " Your score increased by 5 points."
            elif item == "book":
                self.score += 5
                output += " Your score increased by 5 points."
            return output
        else:
            return f"There's no {item} here."

    def examine(self, item):
        if item == "bicycle" and ("bicycle" in self.locations[self.current_location]["items"] or "bicycle" in self.inventory):
            return "The bike has seen better days but it's still usable—barely. The chain is rusted and some of the teeth on its gears are broken."
        elif item == "book" and "book" in self.inventory:
            return "The book is entitled: 'How to Build Anything'. On the cover it shows someone pedaling a bike to generate electricity. That might be useful to know!"
        elif item == "cheez-ees" and "cheez-ees" in self.inventory:
            return "The text on the unopened bag proclaims these are 'Delicious, crispy, cheese-shaped, cheese-flavored crackers.'"
        elif item == "vending machine" and self.current_location == "platform":
            return "Pictures of fizzy drinks are on its side, as well as a cartoon goat. The battered and abused machine appears to be without power."
        elif item == "computer" and self.current_location == "bunker":
            return "It's an ancient machine with a disk drive and a large, rounded glass monitor. It's plugged into a power inverter."
        elif item == "power inverter" and self.current_location == "bunker":
            return "An electrical device. If you could hook up a battery to it, you could use it battery to power this computer."
        elif item == "toolbox" and self.current_location == "bunker":
            return "Yeah, you could build something with this. But what?"
        else:
            return f"You don't see any {item} here to examine."

    def ride_bicycle(self):
        if "bicycle" in self.inventory:
            self.riding_bicycle = True
            return "It's a bumpy ride, but still faster than walking."
        else:
            return "You don't have a bicycle to ride."

    def read_book(self):
        if "book" in self.inventory:
            return "The battery project requires a drive belt, a motor, a battery, a power inverter, jumper cables, some wires and a crank for the motor. You may CONSULT this book about each PART once you start the build."
        else:
            return "You don't have a book to read."

    def interact_vending_machine(self):
        if self.current_location == "platform" and self.locations["platform"]["vending_machine"]:
            self.inventory.append("energy_drink")
            self.score += 5
            return "A can drops out of the machine. You've obtained a can of FLAMING GOAT! energy drink. Your score increased by 5 points."
        else:
            return "There's no vending machine here to interact with."

    def open_can(self):
        if "energy_drink" in self.inventory:
            self.energy_drink_opened = True
            return "You pop the top of the can. It lets out a pleasant 'hssssss...'"
        else:
            return "You don't have an energy drink to open."

    def drink_can(self):
        if "energy_drink" in self.inventory and self.energy_drink_opened:
            self.inventory.remove("energy_drink")
            return "It's warm and sugary sweet. You feel queasy, but invigorated."
        elif "energy_drink" in self.inventory and not self.energy_drink_opened:
            return "You need to open the can first."
        else:
            return "You don't have an energy drink to drink."

    def talk_to(self, person):
        if person == "mutants" and self.current_location == "market":
            return "One of them steps forward. Based on her elaborate headdress, she appears to be the leader of the mutant tribe. 'Have you something to barter?'"
        elif person == "leader" and self.current_location == "market":
            return "Her headdress is fashioned from yellow caution tape, spoons and old soda cans. Around her neck she wears a floppy disk on a string."
        else:
            return f"There's no {person} here to talk to."

    def trade(self):
        if self.current_location == "market" and self.locations["market"]["mutant_leader"]:
            if "energy_drink" in self.inventory:
                if self.energy_drink_opened:
                    self.inventory.remove("energy_drink")
                    self.floppy_disk = True
                    self.score += 5
                    return "'Awww...it's empty. Well, take this.' The mutant leader gives you the floppy disk from around her neck and begins fastening the can to her headdress. Your score increased by 5 points."
                else:
                    self.inventory.remove("energy_drink")
                    self.floppy_disk = True
                    self.score += 10
                    return "'Unopened?! Amazing!' The mutant leader gives you her necklace and cracks open the soda for a refreshing treat. Your score increased by 10 points."
            else:
                return "You don't have anything to trade."
        else:
            return "There's no one here to trade with."

    def build_generator(self):
        required_items = ["motor", "car_battery", "drive_belt", "jumper_cables", "wires", "bicycle"]
        if all(item in self.inventory for item in required_items):
            self.generator_built = True
            self.score += 10
            return "Using the instructions from the book, you begin to assemble the generator...\n" + \
                   "You attach the drive belt to the bicycle's rear wheel and the motor...\n" + \
                   "Next, you connect the motor to the car battery using the jumper cables...\n" + \
                   "Finally, you run wires from the battery to the power inverter...\n" + \
                   "Success! You've built a bicycle-powered generator! Your score increased by 10 points."
        else:
            missing_items = [item for item in required_items if item not in self.inventory]
            return f"You don't have all the necessary parts. You're missing: {', '.join(missing_items)}"

    def attach(self, item1, item2):
        return f"You attach the {item1} to the {item2}."

    def pedal_bike(self):
        if self.generator_built:
            self.computer_powered = True
            self.score += 10
            return "With some effort, you get the chain moving, which turns the motor and generates enough electricity to charge the battery. Your score increased by 10 points."
        else:
            return "You need to build the generator first."

    def turn_on_computer(self):
        if self.current_location == "bunker" and self.computer_powered:
            if self.floppy_disk:
                self.score += 30
                self.is_game_over = True
                return "You flick a switch and the machine chirps, beeps and whirs...then reads the floppy disk inside its drive. The screen flashes with a message:\n" + \
                       "WELCOME TO...ACTION CASTLE!\n" + \
                       "YOU ARE STANDING IN A SMALL COTTAGE. THERE IS A FISHING POLE HERE. A DOOR LEADS OUTSIDE.\n" + \
                       "Your score increased by 30 points.\n" + \
                       "Congratulations! You've completed your journey and unlocked the secrets of the old world!"
            else:
                return "You flick a switch and the machine chirps, beeps and whirs...but that's it."
        elif not self.computer_powered:
            return "The computer has no power. You'll need to find a way to turn it on first."
        else:
            return "There's no computer here to turn on."

    def insert_floppy(self):
        if self.floppy_disk and self.current_location == "bunker":
            return "You insert the floppy disk into the drive."
        elif not self.floppy_disk:
            return "You don't have a floppy disk to insert."
        else:
            return "There's nowhere to insert a floppy disk here."

    def consult_book(self, part):
        if "book" in self.inventory:
            return f"The {part} connects to another part."
        else:
            return "You don't have the book to consult."

    def encounter_rat_people(self):
        output = "Suddenly, several hunched humanoid figures scramble from the darkness—you find yourself surrounded.\n"
        if "cheez-ees" in self.inventory:
            output += "Do you want to throw the CHEEZ-EEs? (yes/no)"
            return output
        else:
            self.game_over("You've been overwhelmed by the rat people.")
            return output + "The rat people advance, their chittering growing louder..."

    def game_over(self, message):
        self.is_game_over = True
        return f"\n{message}\nGame Over! Your final score: {self.score}"

    def get_help(self):
        return "\n".join([
            "Available commands:",
            "look - Examine your surroundings",
            "inventory - Check your inventory",
            "take [item] - Pick up an item",
            "examine [item] - Look closely at an item",
            "ride bicycle - Ride the bicycle if you have it",
            "read book - Read the book if you have it",
            "shake/punch/kick machine - Interact with the vending machine",
            "open can - Open the energy drink",
            "drink can - Drink the opened energy drink",
            "talk to [person] - Talk to someone",
            "trade - Attempt to trade with the mutant leader",
            "build generator - Attempt to build a generator",
            "attach [item] to [item] - Attach two items together",
            "pedal bike - Pedal the bike to generate electricity",
            "turn on computer - Try to turn on the computer",
            "insert floppy - Insert the floppy disk into the computer",
            "consult book about [part] - Consult the book about a specific part",
            "go/move/walk/run [direction] - Move in a direction",
            "[direction] - Move in a direction (e.g., 'north', 'out')",
            "quit - End the game"
        ])

if __name__ == "__main__":
    game = Game()
    game.play()