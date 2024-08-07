import logging
import discord
from discord.ext import commands
import os
import configparser

logger = logging.getLogger(__name__)

class Game:
    def __init__(self):
        self.config = self.load_config()
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
                "items": ["wrecked_bike", "vending_machine"],
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
                "items": ["motor", "car_battery", "drive_belt", "jumper_cables", "wires", "junk_pile"]
            },
            "bunker": {
                "description": "The bunker seems like a shrine to the Old World: posters of long-dead celebrities are on the walls and board games, plastic figurines and brightly colored boxes of cereal line the shelves. On a desk in the corner is a dusty old computer. A toolbox is here.",
                "exits": {"out": "scrapyard"},
                "items": ["toolbox", "computer", "power_inverter"],
                "computer": True,
                "power_inverter": True
            }
        }
        self.current_location = "ruins"
        self.inventory = []
        self.score = 0
        self.score_reasons = []
        self.riding_bicycle = False
        self.generator_built = False
        self.computer_powered = False
        self.floppy_disk = False
        self.rat_people_distracted = False
        self.is_game_over = False
        self.save_used = False
        self.turns = 0
        self.max_turns = 100
        self.shelves_examined = False
        self.energy_drink_state = "closed"  # Can be "closed", "opened", or "empty"
        self.generator_parts = {
            "drive_belt": False,
            "motor": False,
            "battery": False,
            "power_inverter": False,
            "jumper_cables": False,
            "wires": False
        }
        logger.debug(f"Loaded config in __init__: {self.config}")
        logger.debug(f"Config sections in __init__: {self.config.sections()}")

    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.expanduser('~/Python/.config')
        config.read(config_path)
        return config

    def play(self):
        output = []
        output.append("Welcome to the Ruins of New York!")
        output.append("In this post-apocalyptic adventure, you'll navigate through dangerous terrain,")
        output.append("solve puzzles, and uncover the secrets of the old world.")
        output.append("Type 'help' at any time for a list of commands.")
        output.append(self.look())
        
        logger.debug(f"Config object: {self.config}")
        logger.debug(f"Config sections: {self.config.sections()}")

        # Get the path to the image
        try:
            pictures_folder = self.config['Paths']['pictures_folder']
            logger.debug(f"Pictures folder from config: {pictures_folder}")
            image_path = os.path.join(pictures_folder, 'ruins_of_new_york.png')
            logger.debug(f"Full image path: {image_path}")
            
            if not os.path.exists(image_path):
                logger.warning(f"Image file does not exist: {image_path}")
                image_path = None
        except KeyError as e:
            logger.error(f"Error reading config: {e}")
            logger.debug(f"Config object: {self.config}")
            logger.debug(f"Config sections: {self.config.sections()}")
            image_path = None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            image_path = None
        
        # Return both the intro text and the image path
        return {
            "message": "\n".join(output),
            "image_path": image_path
        }

    def process_command(self, command):
        self.turns += 1
        if self.turns >= self.max_turns:
            return self.game_over("You've run out of time!")

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
                return self.interact_vending_machine(action)
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
        elif action == "throw":
            if len(command) > 1 and command[1] in ["bag", "cheez-ees"]:
                return self.throw_bag()
            else:
                return "Throw what?"
        elif action == "distract":
            if self.current_location == "dark_tunnel":
                return self.throw_bag()
            else:
                return "There's nothing here that needs distracting."
        elif action == "use":
            if len(command) > 1:
                return self.use_item(command[1])
            else:
                return "Use what?"
        elif action == "drop":
            if len(command) > 1:
                return self.drop_item(command[1])
            else:
                return "Drop what?"
        elif action == "save":
            return self.save_game()
        elif action == "score":
            return self.show_score()
        elif action == "map":
            return self.show_map()
        elif action == "hint":
            return self.get_hint()
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
        
        if new_location == "dark_tunnel":
            return self.enter_dark_tunnel()
        
        self.current_location = new_location
        logger.info(f"Moved to new location: {self.current_location}")
        return self.look()

    def enter_dark_tunnel(self):
        if self.riding_bicycle:
            self.current_location = "dark_tunnel"
            return "You pedal through the dark tunnel as if your life depended on it—and it does! " + self.look()
        elif self.rat_people_distracted:
            self.current_location = "dark_tunnel"
            return "You carefully sneak through the tunnel, the distracted rat people paying you no mind. " + self.look()
        else:
            return self.encounter_rat_people()

    def encounter_rat_people(self):
        output = "After traveling through the tunnel for what seems like forever, several hunched humanoid figures scramble from the darkness—you find yourself surrounded.\n"
        if "cheez-ees" in self.inventory:
            output += "The rat people look hungry. Maybe you could distract them with something? (Hint: try 'throw bag' or 'use cheez-ees')"
        else:
            output += "The rat people advance, their chittering growing louder. You have no way to distract them!"
            self.game_over("You've been overwhelmed by the rat people.")
        return output

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
        if self.current_location == "store" and not self.shelves_examined:
            return "You need to examine the shelves first to see what's available."
        if item in loc["items"]:
            loc["items"].remove(item)
            self.inventory.append(item)
            output = f"You picked up the {item}."
            if item == "cheez-ees":
                self.update_score(5, "Picking up CHEEZ-EEs")
                output += " Your score increased by 5 points."
            elif item == "book":
                self.update_score(5, "Picking up the book")
                output += " Your score increased by 5 points."
            return output
        else:
            return f"There's no {item} here."

    def examine(self, item):
        loc = self.locations[self.current_location]

        if item == "shelves" and self.current_location == "store":
            self.shelves_examined = True
            return "Amidst the trash you find the last remaining bag of CHEEZ-EEs and a book."
        elif item in loc["items"] or item in self.inventory:
            if item == "bicycle":
                return "The bike has seen better days but it's still usable—barely. The chain is rusted and some of the teeth on its gears are broken."
            elif item == "book":
                return "The book is entitled: 'How to Build Anything'. On the cover it shows someone pedaling a bike to generate electricity. That might be useful to know!"
            elif item == "cheez-ees":
                return "The text on the unopened bag proclaims these are 'Delicious, crispy, cheese-shaped, cheese-flavored crackers.'"
            elif item == "vending_machine" and self.current_location == "platform":
                return "Pictures of fizzy drinks are on its side, as well as a cartoon goat. The battered and abused machine appears to be without power."
            elif item == "computer" and self.current_location == "bunker":
                return "It's an ancient machine with a disk drive and a large, rounded glass monitor. It's plugged into a power inverter."
            elif item == "power_inverter" and self.current_location == "bunker":
                return "An electrical device. If you could hook up a battery to it, you could use it battery to power this computer."
            elif item == "toolbox" and self.current_location == "bunker":
                return "Yeah, you could build something with this. But what?"
            elif item == "wrecked_bike" and self.current_location == "platform":
                return "The bike is damaged beyond repair. The front wheel is warped from hitting the metal rails."
            elif item == "junk_pile" and self.current_location == "scrapyard":
                return "You find some useful car parts in amongst the trash. There's an old motor, a car battery, a drive belt, jumper cables and wires. Alas, the car battery is dead."
            elif item == "energy_drink":
                if self.energy_drink_state == "closed":
                    return "An unopened can of FLAMING GOAT! energy drink."
                elif self.energy_drink_state == "opened":
                    return "An opened can of FLAMING GOAT! energy drink."
                else:
                    return "An empty can of FLAMING GOAT! energy drink."
            elif item in ["motor", "car_battery", "drive_belt", "jumper_cables", "wires"] and self.current_location == "scrapyard":
                return f"A {item} that could be useful for building something."
            else:
                return f"You see a {item}. It doesn't seem particularly noteworthy."
        elif item == "figures" and self.current_location == "dark_tunnel":
            return "They walk like humans but chitter like rodents; you see their beady red eyes and flashes of sharp white teeth—like some kind of...rat people!"
        elif item == "tunnel" and self.current_location == "tunnel_entrance":
            return "It will take you beneath the river to the other side. Traveling on foot could be dangerous—best to find a faster way to get to the other side."
        elif item == "people" and self.current_location == "market":
            return "Mutants. They wear armor forged from salvaged street signs and they carry various devices used to stab, slash, smash and crush. They are fearsome to behold but not overtly aggressive...yet."
        elif item == "leader" and self.current_location == "market":
            return "Her headdress is fashioned from yellow caution tape, spoons and old soda cans. Around her neck she wears a floppy disk on a string."
        elif item == "canal" and self.current_location == "burning_canal":
            return "The water is a toxic soup, with patches of burning oil creating an eerie, dangerous atmosphere."
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

    def interact_vending_machine(self, action):
        if self.current_location == "platform" and "vending_machine" in self.locations["platform"]["items"]:
            if action in ["shake", "punch", "kick"]:
                self.inventory.append("energy_drink")
                self.update_score(5, "Getting energy drink from vending machine")
                return f"You {action} the vending machine. A can drops out. You've obtained a can of FLAMING GOAT! energy drink. Your score increased by 5 points."
            else:
                return f"You can't {action} the vending machine."
        else:
            return "There's no vending machine here to interact with."

    def open_can(self):
        if "energy_drink" in self.inventory:
            if self.energy_drink_state == "closed":
                self.energy_drink_state = "opened"
                return "You pop the top of the can. It lets out a pleasant 'hssssss...'"
            elif self.energy_drink_state == "opened":
                return "The can is already opened."
            else:
                return "The can is empty."
        else:
            return "You don't have an energy drink to open."

    def drink_can(self):
        if "energy_drink" in self.inventory:
            if self.energy_drink_state == "closed":
                return "You need to open the can first."
            elif self.energy_drink_state == "opened":
                self.energy_drink_state = "empty"
                return "It's warm and sugary sweet. You feel queasy, but invigorated."
            else:
                return "The can is empty."
        else:
            return "You don't have an energy drink to drink."

    def talk_to(self, person):
        if person == "mutants" and self.current_location == "market":
            return "One of them steps forward. Based on her elaborate headdress, she appears to be the leader of the mutant tribe. 'Have you something to barter?'"
        elif person == "leader" and self.current_location == "market":
            return "Her headdress is fashioned from yellow caution tape, spoons and old soda cans. Around her neck she wears a floppy disk on a string. She asks, 'An offering for The Great Oracle, perhaps?'"
        else:
            return f"There's no {person} here to talk to."

    def trade(self):
        if self.current_location == "market" and self.locations["market"]["mutant_leader"]:
            if "energy_drink" in self.inventory:
                if self.energy_drink_state == "empty":
                    self.inventory.remove("energy_drink")
                    self.floppy_disk = True
                    self.update_score(5, "Trading empty energy drink for floppy disk")
                    return "'Awww...it's empty. Well, take this.' The mutant leader gives you the floppy disk from around her neck and begins fastening the can to her headdress. Your score increased by 5 points."
                elif self.energy_drink_state == "closed":
                    self.inventory.remove("energy_drink")
                    self.floppy_disk = True
                    self.update_score(10, "Trading full energy drink for floppy disk")
                    return "'Unopened?! Amazing!' The mutant leader gives you her necklace and cracks open the soda for a refreshing treat. Your score increased by 10 points."
                else:
                    return "The mutant leader doesn't seem interested in your opened can."
            else:
                return "You don't have anything to trade."
        else:
            return "There's no one here to trade with."

    def build_generator(self):
        if all(self.generator_parts.values()):
            self.generator_built = True
            self.update_score(10, "Building the generator")
            return "Success! You've built a bicycle-powered generator! Your score increased by 10 points."
        else:
            missing_parts = [part for part, attached in self.generator_parts.items() if not attached]
            return f"The generator is not complete. You still need to attach: {', '.join(missing_parts)}"

    def attach(self, item1, item2):
        if item1 in self.generator_parts and item1 in self.inventory:
            if item2 in ["bicycle", "generator"]:
                self.generator_parts[item1] = True
                self.inventory.remove(item1)
                return f"You've attached the {item1} to the {item2}."
            else:
                return f"You can't attach the {item1} to the {item2}."
        else:
            return f"You don't have a {item1} to attach."

    def pedal_bike(self):
        if self.generator_built:
            self.computer_powered = True
            self.update_score(10, "Powering up the computer")
            return "With some effort, you get the chain moving, which turns the motor and generates enough electricity to charge the battery. Your score increased by 10 points."
        else:
            return "You need to build the generator first."

    def turn_on_computer(self):
        if self.current_location == "bunker":
            if self.computer_powered:
                if self.floppy_disk:
                    self.update_score(30, "Activating the computer with the floppy disk")
                    if not self.save_used:
                        self.update_score(5, "Completing the game without saving")
                    self.is_game_over = True
                    return "You flick a switch and the machine chirps, beeps and whirs...then reads the floppy disk inside its drive. The screen flashes with a message:\n" + \
                           "WELCOME TO...ACTION CASTLE!\n" + \
                           "YOU ARE STANDING IN A SMALL COTTAGE. THERE IS A FISHING POLE HERE. A DOOR LEADS OUTSIDE.\n" + \
                           f"Your score increased by {30 if self.save_used else 35} points.\n" + \
                           "Congratulations! You've completed your journey and unlocked the secrets of the old world!"
                else:
                    return "You flick a switch and the machine chirps, beeps and whirs...but that's it."
            else:
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
            if part in ["drive belt", "motor", "battery", "power inverter", "jumper cables", "wires", "crank"]:
                return f"The book says: The {part} is an essential component of the generator."
            else:
                return f"The book doesn't have any specific information about {part}."
        else:
            return "You don't have the book to consult."

    def throw_bag(self):
        if "cheez-ees" in self.inventory and self.current_location == "dark_tunnel":
            self.inventory.remove("cheez-ees")
            self.rat_people_distracted = True
            self.update_score(15, "Distracting rat people")
            return "The rat people scurry to collect their cheesy prize, turning their backs on you for a brief moment. You've successfully distracted them!"
        elif "cheez-ees" in self.inventory:
            return "You throw the bag of CHEEZ-EEs, but nothing happens. Maybe save it for when you really need it?"
        else:
            return "You don't have any CHEEZ-EEs to throw."

    def use_item(self, item):
        if item == "bicycle" and "bicycle" in self.inventory:
            return self.ride_bicycle()
        elif item == "book" and "book" in self.inventory:
            return self.read_book()
        elif item == "cheez-ees" and "cheez-ees" in self.inventory:
            if self.current_location == "dark_tunnel":
                return self.throw_bag()
            else:
                return "You don't need to use the CHEEZ-EEs right now."
        elif item == "energy_drink" and "energy_drink" in self.inventory:
            if self.energy_drink_state == "opened":
                return self.drink_can()
            else:
                return self.open_can()
        else:
            return f"You can't use the {item} right now."

    def drop_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
            self.locations[self.current_location]["items"].append(item)
            return f"You drop the {item}."
        else:
            return f"You don't have a {item} to drop."

    def save_game(self):
        self.save_used = True
        return "Game saved. Note that using save will reduce your final score."

    def update_score(self, points, reason):
        self.score += points
        self.score_reasons.append(f"{reason}: {points} points")

    def show_score(self):
        output = f"Your current score is: {self.score}\n"
        output += "Score breakdown:\n"
        for reason in self.score_reasons:
            output += f"- {reason}\n"
        return output

    def show_map(self):
        map_text = """
        Tunnel
        Entrance
        Dark Tunnel
        Platform
        Scrapyard
        Market
        Bunker
        Ruins of
        New York
        Burning
        Canal
        Looted
        Store
        """
        return map_text

    def get_hint(self):
        if self.current_location == "ruins":
            return "Try examining and taking items you see. The bicycle might be useful later."
        elif self.current_location == "dark_tunnel" and not self.rat_people_distracted:
            return "The rat people look hungry. Maybe you have something to distract them?"
        elif self.current_location == "market":
            return "The mutant leader seems interested in trading. Do you have anything valuable?"
        elif self.current_location == "bunker" and not self.computer_powered:
            return "The computer needs power. Perhaps you could build something to generate electricity?"
        else:
            return "Keep exploring and examining items. The key to progress is often in the details."

    def game_over(self, message):
        self.is_game_over = True
        return f"\n{message}\nGame Over! Your final score: {self.score} (in {self.turns} turns)"

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
            "throw [item] - Throw an item",
            "distract - Try to distract nearby creatures",
            "use [item] - Use an item in your inventory",
            "drop [item] - Drop an item from your inventory",
            "trade - Attempt to trade with the mutant leader",
            "build generator - Attempt to build a generator",
            "attach [item] to [item] - Attach two items together",
            "pedal bike - Pedal the bike to generate electricity",
            "turn on computer - Try to turn on the computer",
            "insert floppy - Insert the floppy disk into the computer",
            "consult book about [part] - Consult the book about a specific part",
            "go/move/walk/run [direction] - Move in a direction",
            "[direction] - Move in a direction (e.g., 'north', 'out')",
            "save - Save your game (reduces final score)",
            "score - Show your current score",
            "map - Display a map of the game world",
            "hint - Get a hint if you're stuck",
            "quit - End the game"
        ])

if __name__ == "__main__":
    game = Game()
    game.play()