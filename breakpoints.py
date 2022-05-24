import sublime
import sublime_plugin
import os.path
import re

def log(text):
	print('breakpoints:', text)

class Breakpoints:
	def read(self):
		raise NotImplementedError()

	def write(self):
		raise NotImplementedError()

	def create(file, line):
		return (file, line)

class LldbBreakpointsFile(Breakpoints):
	pattern = re.compile('b\\s+([^:]+):(\\d+)')

	def __init__(self, path):
		self.path = path

	def read(self):
		result = []

		with open(self.path, 'r') as file:
			for entry in [l.rstrip() for l in file.readlines()]:
				m = LldbBreakpointsFile.pattern.match(entry)
				if m:
					path = str(m.group(1))
					line = int(m.group(2))
					result += [Breakpoints.create(path, line)]
					log('loaded {0}:{1}.'.format(path, line))

		return result

	def write(self, breakpoints):
		count = 0

		with open(self.path, 'w') as file:
			file.write('# command source {0}\n\n'.format(self.path))

			for breakpoint in breakpoints:
				file.write('b {0}:{1}\n'.format(*breakpoint))
				count = count + 1

class ToggleBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		breakpoints = [self.view.rowcol(r.a)[0] for r in self.view.get_regions('breakpoints')]

		for selected in self.view.sel():
			line = self.view.rowcol(selected.a)[0]

			if line in breakpoints:
				breakpoints.remove(line)
			else:
				breakpoints += [line]

		breakpoints.sort()
		points = [self.view.text_point(b, 0) for b in breakpoints]
		regions = [sublime.Region(p, p) for p in points]
		
		self.view.add_regions('breakpoints', regions=regions, scope="region.bluish", icon="dot")

class Listener(sublime_plugin.ViewEventListener):
	def directory(self, window):
		if window.project_file_name():
			return os.path.dirname(window.project_file_name())
		elif window.workspace_file_name():
			return os.path.dirname(window.workspace_file_name())
		else:
			return window.folders()[0]

	def on_load_async(self):
		file = LldbBreakpointsFile(os.path.join(self.directory(self.view.window()), '.breakpoints'))
		regions = []

		log('loading breakpoints from {0}.'.format(file.path))

		for path, line in file.read():
			if path == self.view.file_name():
				offset = self.view.text_point(line - 1, 0)
				regions += [sublime.Region(offset, offset)]

		self.view.add_regions(
			'breakpoints',
			regions=regions,
			scope="region.bluish", icon="dot"
		)

		log('{0} breakpoints loaded.'.format(len(regions)))

	def on_post_save_async(self):
		file = LldbBreakpointsFile(os.path.join(self.directory(self.view.window()), '.breakpoints'))
		has_breakpoints = bool(self.view.get_regions('breakpoints'))
		had_breakpoints = 0 
		breakpoints = []

		try:
			breakpoints = file.read()
			had_breakpoints = len(breakpoints)
			breakpoints = list(filter(lambda b: b[0] != self.view.file_name(), breakpoints))
		except FileNotFoundError:
			pass

		had_breakpoints = bool(had_breakpoints > len(breakpoints))

		for region in self.view.get_regions('breakpoints'):
			path = self.view.file_name()
			line = self.view.rowcol(region.a)[0] + 1
			breakpoints += [Breakpoints.create(path, line)]

		breakpoints.sort()

		if (has_breakpoints or had_breakpoints):
			log('saving breakpoints to {0}.'.format(file.path))
			file.write(breakpoints)
			log('{0} breakpoints saved.'.format(len(breakpoints)))
