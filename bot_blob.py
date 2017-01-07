'''
	@ Harris Christiansen (Harris@HarrisChristiansen.com)
	January 2016
	Generals.io Automated Client - https://github.com/harrischristiansen/generals-bot
	Bot_blob: Creates a blob of troops.
'''

import logging
import random
import threading
import time

import client.generals as generals
from viewer import GeneralsViewer

# Show all logging
logging.basicConfig(level=logging.DEBUG)

class GeneralsBot(object):
	def __init__(self):
		# Start Game Loop
		_create_thread(self._start_game_loop)

		# Start Game Viewer
		self._viewer = GeneralsViewer()
		self._viewer.mainViewerLoop()

	def _start_game_loop(self):
		# Create Game
		#self._game = generals.Generals('PurdueBot', 'PurdueBot', 'private', gameid='HyI4d3_rl') # Private Game - http://generals.io/games/HyI4d3_rl
		#self._game = generals.Generals('PurdueBot', 'PurdueBot', '1v1') # 1v1
		self._game = generals.Generals('PurdueBot', 'PurdueBot', 'ffa') # FFA

		# Start Game Update Loop
		_create_thread(self._start_update_loop)

		while (True):
			msg = input('Send Msg:')
			print("Sending MSG: " + msg)
			# TODO: Send msg

	######################### Handle Updates From Server #########################

	def _start_update_loop(self):
		firstUpdate = True

		for update in self._game.get_updates():
			self._set_update(update)

			#self._print_scores()

			if (firstUpdate):
				_create_thread(self._start_moves)
				firstUpdate = False

			# Update GeneralsViewer Grid
			if '_viewer' in dir(self):
				self._viewer.updateGrid(self._update['tile_grid'], self._update['army_grid'])

	def _set_update(self, update):
		if (update['complete']):
			print("!!!! Game Complete. Result = " + str(update['result']) + " !!!!")
			return

		self._update = update
		self._pi = update['player_index']
		self._opponent_position = None
		self._rows = update['rows']
		self._cols = update['cols']

		self._record_opponent_position()

	def _print_scores(self):
		scores = sorted(self._update['scores'], key=lambda general: general['total'], reverse=True) # Sort Scores
		lands = sorted(self._update['lands'], reverse=True)
		armies = sorted(self._update['armies'], reverse=True)

		print(" -------- Scores --------")
		for score in scores:
			pos_lands = lands.index(score['tiles'])
			pos_armies = armies.index(score['total'])

			if (score['i'] == self._pi):
				print("SELF: ")
			print('Land: %d (%4d), Army: %d (%4d) / %d' % (pos_lands+1, score['tiles'], pos_armies+1, score['total'], len(scores)))

	######################### Thread: Make Moves #########################

	def _start_moves(self):
		while (not self._update['complete']):
			self._expand_blob()
			self._run_chains_distribution()
			self._dumb_distribute()

	######################### Record Opponent Position #########################

	def _record_opponent_position(self):
		largestArmy = 0

		for x in _shuffle(range(self._cols)): # Check Each Square
			for y in _shuffle(range(self._rows)):
				source_tile = self._update['tile_grid'][y][x]
				source_army = self._update['army_grid'][y][x]
				if (source_tile >= 0 and source_tile != self._pi and source_army > largestArmy): # Find Opponent with largest armies
					self._opponent_position = (x,y)
					print("Found Opponent: "+str(self._opponent_position))
					largestArmy = source_army
					

	######################### Expand Blob #########################

	def _expand_blob(self):
		for x in _shuffle(range(self._cols)): # Check Each Square
			for y in _shuffle(range(self._rows)):
				source_tile = self._update['tile_grid'][y][x]
				source_army = self._update['army_grid'][y][x]
				if (source_tile == self._pi and source_army >= 2): # Find One With Armies
					for dy, dx in self._explore_moves(x,y):
						if (self._validPosition(x+dx,y+dy)):
							dest_tile = self._update['tile_grid'][y+dy][x+dx]
							dest_army = self._update['army_grid'][y+dy][x+dx]
							if (dest_army > 0):
								dest_army += 2
							if (dest_tile != self._pi and source_army > dest_army): # Capture Somewhere New
								self._place_move(y, x, y+dy, x+dx)

	######################### Dumb Distribute #########################

	def _dumb_distribute(self):
		for x in _shuffle(range(self._cols)): # Check Each Square
			for y in _shuffle(range(self._rows)):
				source_tile = self._update['tile_grid'][y][x]
				source_army = self._update['army_grid'][y][x]
				if (source_tile == self._pi and source_army > 6): # Find One With Armies
					for dy, dx in self._explore_moves(x,y):
						if (self._validPosition(x+dx,y+dy)):
							dest_tile = self._update['tile_grid'][y+dy][x+dx]
							dest_army = self._update['army_grid'][y+dy][x+dx]
							if (source_army > (dest_army * 2)): # Position has less army count
								if (self._place_move(y, x, y+dy, x+dx, move_half=True)):
									return


	######################### Run Chains Distribution #########################

	def _run_chains_distribution(self):
		distribution_path = []

		for x in _shuffle(range(self._cols)): # Check Each Square
			for y in _shuffle(range(self._rows)):
				source_tile = self._update['tile_grid'][y][x]
				source_army = self._update['army_grid'][y][x]
				if (source_tile == self._pi and source_army > 12): # Find One With Armies
					distribution_path = self._distribute_square(distribution_path, x, y)

	def _distribute_square(self, path, x, y):
		if (not self._validPosition(x,y)):
			return path

		source_tile = self._update['tile_grid'][y][x]
		source_army = self._update['army_grid'][y][x]

		if (source_army < 3):
			return path

		if (path == None):
			path = []

		if ((x,y) in path):
			return path
		path.append((x,y))

		for dy, dx in self._explore_moves(x,y):
			if (self._validPosition(x+dx,y+dy)):
				dest_tile = self._update['tile_grid'][y+dy][x+dx]
				dest_army = self._update['army_grid'][y+dy][x+dx]
				if (dest_army > 0):
					dest_army += 2
				if (dest_tile != self._pi and source_army > dest_army): # Capture Somewhere New
					self._place_move(y, x, y+dy, x+dx)
					#time.sleep(1) # Wait for next move
					return self._distribute_square(path, x+dx, y+dy)

				if (source_army > (dest_army + 2)): # Position has less army count
					self._place_move(y, x, y+dy, x+dx)
					#time.sleep(1) # Wait for next move
					return self._distribute_square(path, x+dx, y+dy)

	######################### Move Placement Helpers #########################
	
	def _explore_moves(self, x, y):
		positions = self._directional_moves(x,y)
		first_positions = []
		for dy, dx in positions:
			if (self._validPosition(x+dx,y+dy)):
				dest_tile = self._update['tile_grid'][y+dy][x+dx]
				dest_army = self._update['army_grid'][y+dy][x+dx]
				if (dest_tile != -1 and dest_tile != self._pi):
					first_positions.append((dy,dx))
					positions.remove((dy,dx))

		first_positions.extend(positions)
		return first_positions

	def _directional_moves(self, x, y):
		if (self._opponent_position != None):
			return self._toward_opponent_moves(x,y)
		
		return self._away_king_moves(x,y)


	def _toward_opponent_moves(self, x, y):
		opp_x, opp_y = self._opponent_position
		print("Moving Toward Opponent")

		if y > opp_y:
			if x > opp_x: # dy=-1, dx=-1
				moves = random.sample([(-1, 0), (0, -1)],2)
				moves.extend(random.sample([(1, 0), (0, 1)],2))
				return moves
			else: # dy=-1, dx=1
				moves = random.sample([(0, 1), (-1, 0)],2)
				moves.extend(random.sample([(1, 0), (0, -1)],2))
				return moves
		else:
			if x > opp_x: # dy=1, dx=-1
				moves = random.sample([(1, 0), (0, -1)],2)
				moves.extend(random.sample([(-1, 0), (0, 1)],2))
				return moves
			else: # dy=1, dx=1
				moves = random.sample([(0, 1), (1, 0)],2)
				moves.extend(random.sample([(-1, 0), (0, -1)],2))
				return moves

	def _away_king_moves(self, x, y):
		king_y, king_x = self._update['generals'][self._pi]

		if (y == king_y and x == king_x): # Moving from king
			return self._moves_random()

		if y > king_y:
			if x > king_x: # dy=1, dx=1
				moves = random.sample([(1, 0), (0, 1)],2)
				moves.extend(random.sample([(-1, 0), (0, -1)],2))
				return moves
			else: # dy=1, dx=-1
				moves = random.sample([(0, -1), (1, 0)],2)
				moves.extend(random.sample([(-1, 0), (0, 1)],2))
				return moves
		else:
			if x > king_x: # dy=-1, dx=1
				moves = random.sample([(-1, 0), (0, 1)],2)
				moves.extend(random.sample([(1, 0), (0, -1)],2))
				return moves
			else: # dy=-1, dx=-1
				moves = random.sample([(0, -1), (-1, 0)],2)
				moves.extend(random.sample([(1, 0), (0, 1)],2))
				return moves


	def _moves_random(self):
		return random.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4)

	def _place_move(self, y1, x1, y2, x2, move_half=False):
		if (self._validPosition(x2, y2)):
			self._game.move(y1, x1, y2, x2, move_half)
			print(str(time.time())+" - Made Move")
			time.sleep(0.8)

			# Update Current Board
			#self._update['tile_grid'][y2][x2] = self._pi
			#self._update['army_grid'][y2][x2] = self._update['army_grid'][y1][x1] - self._update['army_grid'][y2][x2] - 1
			#self._update['army_grid'][y1][x1] = 1
			return True
		return False

	def _validPosition(self, x, y):
		return 0 <= y < self._rows and 0 <= x < self._cols and self._update['tile_grid'][y][x] != generals.MOUNTAIN

######################### Global Helpers #########################

def _create_thread(f):
	t = threading.Thread(target=f)
	t.daemon = True
	t.start()

def _shuffle(seq):
	shuffled = list(seq)
	random.shuffle(shuffled)
	return iter(shuffled)

######################### Main #########################

# Start Bot
GeneralsBot()