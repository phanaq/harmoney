valid_numeral_diffs = [0, 2, 4]

class HarmonyDetector():
	def __init__(self, mode, tonic):
		self.mode = mode
		self.tonic = tonic
		self.scale = Scale(self.mode, self.tonic)

		self.diff_to_closest_harmony = 0
		self.harmony_is_valid = False

	def check_harmony(self, melody_pitch, input_pitch):
		# print 'melody_pitch:', melody_pitch
		# print 'input_pitch:', input_pitch
		valid_harmonic_steps = self._get_valid_harmonic_steps(melody_pitch)
		input_step = input_pitch % 12
		if input_step in valid_harmonic_steps:
			diff_to_closest_harmony = 0
			harmony_is_valid = True
		else:
			diff_to_closest_harmony = 100
			closest_harmony = None
			for valid_step in valid_harmonic_steps:
				diff_to_harmony = valid_step - input_step
				if abs(diff_to_harmony) < abs(diff_to_closest_harmony):
					diff_to_closest_harmony = diff_to_harmony
			harmony_is_valid = False

		self.diff_to_closest_harmony = diff_to_closest_harmony
		self.harmony_is_valid = harmony_is_valid

		return [self.diff_to_closest_harmony, self.harmony_is_valid]
		# print 'diff_to_closest_harmony:', self.diff_to_closest_harmony
		# print 'harmony_is_valid:', self.harmony_is_valid
		# print ''

	def _get_valid_harmonic_steps(self, melody_pitch):
		melody_numeral = self.scale.get_numeral(melody_pitch)
		valid_harmonic_steps = set([])
		for valid_numeral_diff in valid_numeral_diffs:
			valid_harmonic_numeral = (melody_numeral + valid_numeral_diff) % 12
			valid_harmonic_step = self.scale.get_step(valid_harmonic_numeral)
			valid_harmonic_steps.add(valid_harmonic_step)
		return valid_harmonic_steps


step_intervals = {
	'major': [0, 2, 4, 5, 7, 9, 11],
	'minor': [0, 2, 3, 5, 7, 8, 10]
}

class Scale():
	def __init__(self, mode, tonic):
		if mode not in step_intervals.keys():
			raise AttributeError("Mode must be 'major' or 'minor'")
		self.mode = mode
		self.tonic = tonic
		self.valid_steps = set(step_intervals[self.mode])
		self.numerals_to_steps, self.steps_to_numerals = self._get_dicts()

	def get_numeral(self, pitch):
		# Return roman numeral associated with midi pitch
		# Does not handle pitches that are not within the scale
		steps = (pitch - self.tonic) % 12
		return self.steps_to_numerals[steps]

	def get_step(self, numeral):
		# Return number of half steps away from the tonic 
		# associated with roman numeral
		while numeral > 7:
			numeral -= 7
		return self.numerals_to_steps[numeral]

	def _get_dicts(self):
		numerals_to_steps = {}
		steps_to_numerals = {}
		scale_intervals = list(range(1,8))
		steps = step_intervals[self.mode]
		for i, scale_interval in enumerate(scale_intervals):
			numerals_to_steps[scale_interval] = steps[i]
			steps_to_numerals[steps[i]] = scale_interval
		return [numerals_to_steps, steps_to_numerals]

# Test Cases
# h = HarmonyDetector('major', 60)
# h.check_harmony(60, 64)
# h.check_harmony(60, 67)
# h.check_harmony(72, 64)
# h.check_harmony(64, 67)
# h.check_harmony(64, 68)
# h.check_harmony(64, 66)
