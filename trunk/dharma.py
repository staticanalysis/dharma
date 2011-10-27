#!/usr/bin/python

# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, random, re, getopt, math, shutil

class dharma_const:
	VOID_SECTION = 0
	VALUE_SECTION = 1
	VARIABLE_SECTION = 2
	VARIANCE_SECTION = 3
	SUBVARIANCE_SECTION = 4

	TOP_LEVEL = 0;
	ASSIGN_LEVEL = 1

	GENERATE_REPEAT_MAX = 8 
	GENERATE_VARIABLE_MAX = 5
	GENERATE_NEW_VARIABLE_RATIO = 0.1

	VARIANCE_MIN = 1
	VARIANCE_MAX = 1
	VARIANCE_PREFIX = ""
	VARIANCE_SUFFIX = ""

	DHARMA_ARGS = "f:i:n:o:p:s:t:"
	DEFAULT_COUNT = 1
	DEFAULT_TABS = 0
	DEFAULT_FILETYPE = "html"
	MAX_REPEAT_POWER = 12

	LEAF_TRIGGER = 256

	IMPORT_TMP = "import_tmp"

class dharma_object:
	depth = 0

	def __init__(self, ident):
		self.ident = ident
		self.value_xref = {}
		self.variable_xref = {}
		self.element_xref = {}
		return

	def add_value_xref(self, value):
		self.value_xref[value] = -1
		return

	def add_variable_xref(self, variable):
		self.variable_xref[variable] = -1
		return

	def add_element_xref(self, element):
		self.element_xref[element] = -1
		return

	def eval_variable_xref(self, token):
		m = re.search("\!(?P<xref>[a-zA-Z0-9_]+)\!", token)

		if m == None:
			return token

		xref = m.group("xref")

		if not xref in self.variable_xref:
			print "e: variable xref inconsistency in " + self.ident + " looking for " + xref + " on token " + token
			sys.exit(-1)

		prefix = token[:m.start("xref")-1]

		variable = self.variable_xref[xref].generate()
		
		suffix = token[m.end("xref")+1:]

		suffix = self.eval_variable_xref(suffix)

		return prefix + variable + suffix

	def eval_value_xref(self, token):
		m = re.search("\+(?P<xref>[a-zA-Z0-9_]+)\+", token)

		if m == None:
			return token

		xref = m.group("xref")

		if not xref in self.value_xref:
			print "e: value xref inconsistency in " + self.ident + " for " + xref
			sys.exit(-1)

		prefix = token[:m.start("xref")-1]

		value = self.value_xref[xref].generate()

		suffix = token[m.end("xref")+1:]

		suffix = self.eval_value_xref(suffix)

		return prefix + value + suffix

	def eval_element_xref(self, token):
		m = re.search("\@(?P<xref>[a-zA-Z0-9_]+)\@", token)

		if m == None:
			return token

		xref = m.group("xref")

		if not xref in self.element_xref:
			print "e: element xref inconsistency in " + self.ident + " for " + xref
			sys.exit(-1)

		prefix = token[:m.start("xref")-1]
		element = self.element_xref[xref].new_element()
		suffix = token[m.end("xref")+1:]

		suffix = self.eval_element_xref(suffix)

		return prefix + element + suffix

	def eval_meta(self, line):
		line = self.meta_repeat(line)
		line = self.meta_range(line)

		return line

	def meta_repeat(self, line):
		m = re.search("\%repeat\%\((?P<repval>.*?)\)", line, re.S)

		if m == None:
			return line

		repval = m.group("repval")

		s = re.search("(?P<repval>.*),[ ]*\"(?P<sepval>.*?)\"[ ]*$", repval, re.S)

		if s != None:
			repval = s.group("repval")
			sepval = s.group("sepval")
		else:
			sepval = ""

		prefix = line[:m.start()]
		suffix = line[m.end():]

		nrep_max = math.pow(2, random.randint(1, dharma_const.MAX_REPEAT_POWER))
		nrep = random.randint(1,nrep_max)

		out = prefix

		for i in range(0, nrep):
			out += repval
			if i != nrep - 1:
				out += sepval

		out += suffix

		out = self.meta_repeat(out)

		return out

	def meta_range(self, line):
		m = re.search("\%range\%\((?P<rangeval>.*?)\)", line, re.S)

		if m == None:
			return line

		rangeval = m.group("rangeval")

		prefix = line[:m.start()]
		suffix = line[m.end():]

		s = re.match("^(?P<startval>.*)-(?P<endval>.*?)$", rangeval, re.S)

		if s == None:
			print "e: malformed range meta"
			sys.exit(-1)

		startval = s.group("startval")
		endval = s.group("endval")

		if len(startval) == 1 and len(endval) == 1:
			start_idx = ord(startval[0])
			end_idx = ord(endval[0])

			outval = chr(random.randint(start_idx, end_idx))
		elif startval.find(".") == -1:
			# integer range
			if not endval.find(".") == -1:
				print "e: range meta int/float mismatch in " + self.ident
				sys.exit(-1)

			try:
				start_idx = int(startval)
				end_idx = int(endval)
			except:
				print "e: meta range integer conversion error"
				sys.exit(-1)

			outval = str(random.randint(start_idx, end_idx))
		else:
			# floating point range
			if endval.find(".") == -1:
				print "e: range meta float/int mismatch"
				sys.exit(-1)

			try:
				start_idx = float(startval)
				end_idx = float(endval)
			except:
				print "e: meta range float conversion error"
				sys.exit(-1)

			outval = str(random.uniform(start_idx, end_idx))

		out = prefix + outval + suffix

		out = self.meta_range(out)

		return out

class dharma_value(dharma_object):
	leaf_mode = False
	leaf_trigger = 0

	def __init__(self, ident):
		dharma_object.__init__(self, ident)
		self.values = []
		self.leaf = []
		self.leaf_path = []
		return

	def add_value(self, value):
		self.values.append(value)

		m = re.search("\+[a-zA-Z0-9_]+\+", value)

		if m != None:
			return

		m = re.search("\%repeat\%\(.*?\)", value)

		if m != None:
			return

		self.leaf.append(value)

		return

	def add_leaf_path(self, leaf, path, depth):
		self.leaf_path.append((leaf, path, depth))
		return

	def generate(self):
		if dharma_value.leaf_mode == False:
			dharma_value.leaf_trigger += 1

			if dharma_value.leaf_trigger > dharma_const.LEAF_TRIGGER:
				dharma_value.leaf_mode = True

		if len(self.values) == 0:
			return ""
		elif dharma_value.leaf_mode == True:
			if len(self.leaf) != 0:
				sval = random.randint(0, len(self.leaf)-1)
				value = self.leaf[sval]
			else:
				# favour non-repeating
				favourite_values = []
				for val in self.values:
					m = re.search("\%repeat\%\((?P<repval>.*?)\)", val)

					if m == None:
						favourite_values.append(val)

				if len(favourite_values) == 0:
					favourite_values = self.values

				# find the outputs with the smallest number of value references
				minimized_values = []
				for i in range(1, 8):
					if len(minimized_values) != 0:
						break

					for val in favourite_values:
						val_token = val
						count = 0;

						m = re.search("\+[a-zA-Z0-9_]+\+", val_token)

						while m != None:
							count += 1
							val_token = val_token[m.end():]

							m = re.search("\+[a-zA-Z0-9_]+\+", val_token)

						if count <= i:
							minimized_values.append(val)

				if len(minimized_values) == 0:
					minimized_values = favourite_values

				path_idents = []
				for p in self.leaf_path:
					path_idents.append(p[1])

				mv_len = len(minimized_values)
				sval = random.randint(0, mv_len-1)

				for i in range(mv_len):
					out = minimized_values[sval]

					is_leaf_path = True

					suffix = out
					m = re.search("\+(?P<xref>[a-zA-Z0-9_]+)\+", suffix)

					while m != None:
						if not m.group("xref") in path_idents:
							print m.group("xref") + " is not in path_idents"
							is_leaf_path = False

						suffix = suffix[m.end():]
						m = re.search("\+(?P<xref>[a-zA-Z0-9_]+)\+", suffix)

					if is_leaf_path == False:
						sval = (sval + 1) % (len(minimized_values)-1)
					else:
						break

				if is_leaf_path == False:
					print "e: no path to leaf in force-leaf mode in value " + self.ident
					sys.exit(-1)

				value = minimized_values[sval]

		else:
			sval = random.randint(0, len(self.values)-1)

			value = self.values[sval]

		value = self.eval_meta(value)
		value = self.eval_element_xref(value)
		value = self.eval_value_xref(value)
		value = self.eval_variable_xref(value)

		return value

class dharma_variable(dharma_object):
	variable_map = {}

	def __init__(self, ident):
		dharma_object.__init__(self, ident)
		self.variables = []
		self.count = 0
		self.default = ""
		return

	def clear(self):
		self.count = 0
		self.default = ""

	def add_default_variable(self, variable_prefix, variable_suffix):
		self.variables.append((variable_prefix, variable_suffix))
		return

	def new_element(self):
		self.count = self.count + 1
		return self.ident + str(self.count)

	def generate(self):
		if self.count > 0:
			element = random.randint(1, self.count)
			return self.ident + str(element)

		# we have a variable xref before any elements have been contributed, generate a default
		sel = random.randint(0, len(self.variables)-1)

		self.count = 1
		
		variable = self.variables[sel][0] + self.ident + "1" + self.variables[sel][1]

		variable = self.eval_meta(variable)
		variable = self.eval_value_xref(variable)
		variable = self.eval_variable_xref(variable)

		self.default = variable

		return self.ident + "1"
		
class dharma_variance(dharma_object):

	def __init__(self, ident):
		dharma_object.__init__(self, ident)
		self.variances = []
		return

	def add_variance(self, variance):
		self.variances.append(variance)
		return

	def generate(self):
		sel = random.randint(0, len(self.variances)-1)

		base = self.variances[sel]

		base = self.eval_meta(base)
		base = self.eval_element_xref(base)
		base = self.eval_value_xref(base)
		base = self.eval_variable_xref(base)

		return base

class dharma_machine:

	def __init__(self, out, filetype, prefix, suffix, count, tabs):
		self.section = dharma_const.VOID_SECTION
		self.level = dharma_const.TOP_LEVEL
		self.line_number = 0
		self.current_obj = 0
		self.value = {}
		self.variable = {}
		self.variance = {}

		self.out = out.rstrip("/")
		self.filetype = filetype
		self.prefix = prefix
		self.suffix = suffix
		self.count = count
		self.tabs = tabs
	
	def parse_line(self, line):
		self.line_number += 1

		if self.match_comment(line):
			return

		if self.match_const(line):
			self.parse_const(line)
			return

		if self.match_section_assignment(line):
			self.set_section(line)
			return

		if self.match_empty_line(line):
			if obj_type(self.current_obj) == "dharma_object":
				print "e: empty assignment (line %d)" % self.line_number
				sys.exit(-1)
			elif self.current_obj != 0:
				self.add_section_object()

			self.level = dharma_const.TOP_LEVEL
			self.current_obj = 0
			return

		if self.section == dharma_const.VOID_SECTION:
			print "e: non-empty line in void section (line %d)" % self.line_number
			sys.exit(-1)

		if self.level == dharma_const.TOP_LEVEL:
			self.parse_top_level(line)
		elif self.level == dharma_const.ASSIGN_LEVEL:
			self.parse_assign_level(line)

		return

	def parse_top_level(self, line):
		if not self.match_top_level(line):
			print "e: top level syntax error (line %d)" % self.line_number
			sys.exit(-1)

		m = re.match("^(?P<ident>[a-zA-Z0-9_]+) *:= *\n$", line);
		ident_str = m.group("ident")

		self.current_obj = dharma_object(ident_str)

		self.level = dharma_const.ASSIGN_LEVEL

		return

	def parse_assign_level(self, line):
		if not self.match_assign_level(line):
			print "e: assign level syntax error (line %d)" % self.line_number
			sys.exit(-1)

		assign_str = line[1:]

		if self.section == dharma_const.VALUE_SECTION:
			self.parse_assign_value(assign_str)
		elif self.section == dharma_const.VARIABLE_SECTION:
			self.parse_assign_variable(assign_str)
		elif self.section == dharma_const.VARIANCE_SECTION:
			self.parse_assign_variance(assign_str)
		else:
			print "e: invalid state for assignment (line %d)" % self.line_number
			sys.exit(-1)

		self.parse_value_xref(line)
		self.parse_variable_xref(line)
		self.parse_element_xref(line)

		return

	def parse_assign_value(self, value):
		value = value.rstrip("\n")

		tstr = ""

		for t in range(0, self.tabs):
			tstr += "\t"

		value = value.replace("\\n", "\n" + tstr)

		if obj_type(self.current_obj) == "dharma_object":
			value_obj = dharma_value(self.current_obj.ident)
			value_obj.add_value(value)
			self.current_obj = value_obj
		elif obj_type(self.current_obj) == "dharma_value":
			self.current_obj.add_value(value)
		else:
			print "e: normal value found in non-normal assignment (line %d)" % self.line_number
			sys.exit(-1)

		return

	# search token for +value+ style references
	def parse_value_xref(self, token):
		m = re.search("\+(?P<xref>[a-zA-Z0-9_]+)\+", token)

		if not m:	
			return

		xref = m.group("xref")
		self.current_obj.add_value_xref(xref)

		next_token = token.find("+" + xref + "+") + len(xref) + 2
		self.parse_value_xref(token[next_token:])

		return

	# search token for !variable! style references (be careful to not xref a new variable)
	def parse_variable_xref(self, token):
		regex = "\!(?P<xref>[a-zA-Z0-9_]+)\!"

		m = re.search(regex, token)

		if not m:
			return

		xref = m.group("xref")
		self.current_obj.add_variable_xref(xref)

		next_token = token.find("!" + xref + "!") + len(xref) + 2
		self.parse_variable_xref(token[next_token:])

		return

	def parse_element_xref(self, token):
		m = re.search("\@(?P<xref>[a-zA-Z0-0_]+)\@", token)

		if not m:
			return

		xref = m.group("xref")

		self.current_obj.add_element_xref(xref)

		next_token = token[m.end():]
		self.parse_element_xref(next_token)

		return

	def parse_assign_variable(self, variable_line):
		if not self.match_assign_variable(variable_line):
			print "e: variable assignment syntax error (line %d)" % self.line_number
			sys.exit(-1)

		tstr = ""

		for t in range(0, self.tabs):
			tstr += "\t"

		variable_line = variable_line.replace("\\n", "\n" + tstr)
		
		m = re.search("\@(?P<variable>[a-zA-Z0-9_]+)\@", variable_line)

		variable = m.group("variable")

		if variable != self.current_obj.ident:
			print "e: variable name mismatch (line %d)" % self.line_number
			sys.exit(-1)

		prefix_end = m.start("variable") - 1
		suffix_start = m.end("variable") + 1

		prefix = variable_line[:prefix_end]
		suffix = variable_line[suffix_start:].rstrip("\n")

		if obj_type(self.current_obj) == "dharma_object":
			variable_obj = dharma_variable(self.current_obj.ident)
			variable_obj.add_default_variable(prefix, suffix)
			self.current_obj = variable_obj
		elif obj_type(self.current_obj) == "dharma_variable":
			self.current_obj.add_default_variable(prefix, suffix)
		else:
			print "e: inconsistent object for variable assignment (line %d)" % self.line_number
			sys.exit(-1)

		return

	def parse_assign_variance(self, variance_line):
		variance_line = variance_line.rstrip("\n")

		tstr = ""

		for t in range(0, self.tabs):
			tstr += "\t"

		variance_line = variance_line.replace("\\n", "\n" + tstr)

		if obj_type(self.current_obj) == "dharma_object":
			variance_obj = dharma_variance(self.current_obj.ident)
			variance_obj.add_variance(variance_line)
			self.current_obj = variance_obj
		elif obj_type(self.current_obj) == "dharma_variance":
			self.current_obj.add_variance(variance_line)
		else:
			print "e: inconsistent object for variance assignment (line %d)" % self.line_number
			sys.exit(-1)

		return

	def add_section_object(self):
		if self.section == dharma_const.VALUE_SECTION:
			if self.current_obj.ident in self.value:
				print "e: redefining value (line %d)" % self.line_number
				sys.exit(-1)

			self.value[self.current_obj.ident] = self.current_obj
		elif self.section == dharma_const.VARIABLE_SECTION:
			if self.current_obj.ident in self.variable:
				print "e: redefining variable (line %d)" % self.line_number
				sys.exit(-1)

			self.variable[self.current_obj.ident] = self.current_obj
		elif self.section == dharma_const.VARIANCE_SECTION:
			if self.current_obj.ident in self.variance:
				print "e: redefining variance (line %d)" % self.line_number
				sys.exit(-1)
			
			self.variance[self.current_obj.ident] = self.current_obj
		else:
			print "e: inconsistent section value, fatal"
			sys.exit(-1)
		return

	def parse_const(self, line):
		m = re.match("^%const% *(?P<const>[A-Z_]+) *:= *(?P<val>.*)\n$", line)

		const = m.group("const")
		val = m.group("val")

		if not const in dharma_const.__dict__:
			print "e: trying to set non-existent constant (line %d)" % self.line_number
			sys.exit(-1)

		if val[0] == "\"":
			val = val[1:len(val)-1]
			setattr(dharma_const, const, val)
		elif val.find(".") != -1:
			setattr(dharma_const, const, float(val))
		else:
			setattr(dharma_const, const, int(val))

	def match_comment(self, line):
		return re.match("^%%%.*\n$", line)

	def match_const(self, line):
		return re.match("^%const% *[A-Z_]+ *:=.*\n$", line)

	def match_section_assignment(self, line):
		return re.match("^%section% *:= *(value|variable|variance)\n$", line, re.I)

	def match_empty_line(self, line):
		return re.match("^(\n| *\n|\t*\n)$", line)

	def match_top_level(self, line):
		return re.match("^[a-zA-Z0-9_]+ *:= *\n$", line)

	def match_assign_level(self, line):
		return re.match("^\t", line)

	def match_value_range(self, value_line):
		return re.match("^(-|)[0-9]+(\.[0-9]+|)-[0-9]+(\.[0-9]+|)\n$", value_line)

	def match_value_repeater(self, value_line):
		return re.search("\.\.\.", value_line)

	def match_assign_variable(self, variable_line):
		return re.search("\@[a-zA-Z0-9_]+\@", variable_line)

	def set_section(self, line):
		m = re.match("^%section% *:= *(?P<section_mode>\w+)\n$", line, re.I)
		new_section_str = m.group('section_mode').upper() + "_SECTION"
		new_section = getattr(dharma_const, new_section_str)
		self.section = new_section
		return

	def resolve_xref(self):
		self.resolve_section_xref(self.value)
		self.resolve_section_xref(self.variable)
		self.resolve_section_xref(self.variance)

		return

	def resolve_section_xref(self, section):
		for v in section:
			obj = section[v]
			self.resolve_object_xref(obj)

		return

	def resolve_object_xref(self, obj):
		for x in obj.value_xref:
			if not x in self.value:
				print "e: undefined value reference from " + obj.ident + " to " + x
				sys.exit(-1)

			obj.value_xref[x] = self.value[x]

		for x in obj.variable_xref:
			if not x in self.variable:
				print "e: undefined variable reference from " + obj.ident + " to " + x
				sys.exit(-1)

			obj.variable_xref[x] = self.variable[x]

		for x in obj.element_xref:
			if not x in self.variable:
				print "e: element reference without a default variable from " + obj.ident + " to " + x
				sys.exit(-1)

			obj.element_xref[x] = self.variable[x]

		return

	def calculate_leaf_paths(self):
		self.leaf_seen = []
		self.reverse_xref = {}

		# build map of reverse xrefs
		for val in self.value:
			valobj = self.value[val]

			for xref in valobj.value_xref:
				if not xref in self.reverse_xref:
					self.reverse_xref[xref] = list()

				self.reverse_xref[xref].append(valobj.ident)

		# for all leafs, traverse backwards marking path to leaf
		for val in self.value:
			valobj = self.value[val]

			if valobj in self.leaf_seen:
				continue

			if len(valobj.leaf) == 0:
				continue

			self.calculate_leaf_path(valobj)

	def calculate_leaf_path(self, leafobj):
		self.leaf_seen.append(leafobj)

		if not leafobj.ident in self.reverse_xref:
			return

		for xref in self.reverse_xref[leafobj.ident]:
			xrefobj = self.value[xref]

			xrefobj.add_leaf_path(leafobj.ident, leafobj.ident, 0)

			node_seen = [xrefobj]
			self.propogate_leaf(leafobj.ident, xrefobj, node_seen, 1)

	def propogate_leaf(self, leaf, obj, node_seen, depth):
		if not obj.ident in self.reverse_xref:
			return

		for xref in self.reverse_xref[obj.ident]:
			xrefobj = self.value[xref]

			xrefobj.add_leaf_path(leaf, obj.ident, depth)

			if xrefobj in node_seen:
				continue

			node_seen.append(xrefobj)
			self.propogate_leaf(leaf, xrefobj, node_seen, depth+1)

		return

	def generate(self):
		for n in range(1, self.count+1):
			out_file = self.out + "/" + str(n) + "." + self.filetype

			try:
				ofd = open(out_file, 'w')
			except:
				print "e: error opening output file " + out_file
				sys.exit(-1)

			try:
				ofd.write(self.prefix)
			except IOError:
				print "e: error writing prefix section"
				sys.exit(-1)

			for var in self.variable:
				self.variable[var].clear()

			nvar = random.randint(dharma_const.VARIANCE_MIN, dharma_const.VARIANCE_MAX)

			if len(self.variance) == 0:
				print "e: no variances found in grammar"
				sys.exit(-1)

			variance_content = ""

			for i in range(0, nvar):
				svar = random.randint(0, len(self.variance)-1)
				skey = self.variance.keys()[svar]

				dharma_value.leaf_mode = False
				variance = self.variance[skey].generate()

				for t in range(0, self.tabs):
					variance_content += "\t"

				variance_content += dharma_const.VARIANCE_PREFIX
				variance_content += variance
				variance_content += dharma_const.VARIANCE_SUFFIX + "\n"

			variable_content = ""

			for var in self.variable:
				if len(self.variable[var].default) != 0:
					for t in range(0, self.tabs):
						variable_content += "\t"

					variable_content += dharma_const.VARIANCE_PREFIX
					variable_content += self.variable[var].default
					variable_content += dharma_const.VARIANCE_SUFFIX + "\n"

			try:
				ofd.write(variable_content)
				ofd.write(variance_content)
			except:
				print "e: error writing content section"
				sys.exit(1)

			try:
				ofd.write(self.suffix)
			except:
				print "e: error writing suffix section"
				sys.exit(-1)

			ofd.close()
		return

def obj_type(obj):
	return obj.__class__.__name__

def usage():
	print "u: dharma.py -i <input_lx> -o <output_dir> [-n <output_count> -p <prefix_file> -s <suffix_file> -t <tab_count>]"
	return

def main():
	print "dharma"
	print "hawkes 2011\n"

	try:
		opts, args = getopt.getopt(sys.argv[1:], dharma_const.DHARMA_ARGS)
	except getopt.GetoptError, err:
		print "e: " + str(err)
		usage()
		sys.exit(0)

	dharma_filetype = dharma_const.DEFAULT_FILETYPE
	dharma_input = None
	dharma_count = dharma_const.DEFAULT_COUNT
	dharma_output = None
	dharma_prefix = None
	dharma_suffix = None
	dharma_tabs = dharma_const.DEFAULT_TABS

	for o, a in opts:
		if o == "-f":
			dharma_filetype = a
		elif o == "-i":
			dharma_input = a
		elif o == "-n":
			dharma_count = int(a)
		elif o == "-o":
			dharma_output = a
		elif o == "-p":
			dharma_prefix = a
		elif o == "-s":
			dharma_suffix = a
		elif o == "-t":
			dharma_tabs = int(a)
		else:
			print "e: unknown option " + o
			sys.exit(-1)

	if dharma_input == None or dharma_output == None:
		print "e: input and output arguments required"
		usage()
		sys.exit(-1)

	try:
		fd = open(dharma_input, 'r')
	except:
		print "e: error opening language file"
		sys.exit(-1)

	print "i: using language " + dharma_input

	if os.path.isdir(dharma_output) == False:
		print "e: output directory does not exist"
		sys.exit(-1)

	print "i: using output directory " + dharma_output

	try:
		if dharma_prefix != None:
			pfd = open(dharma_prefix, 'r')
			prefix_data = pfd.read()
		else:
			prefix_data = ""

		if dharma_suffix != None:
			sfd = open(dharma_suffix, 'r')
			suffix_data = sfd.read()
		else:
			suffix_data = ""
	except:
		print "e: error reading prefix or suffix file"
		sys.exit(-1)

	dharma = dharma_machine(dharma_output, dharma_filetype, prefix_data, suffix_data, dharma_count, dharma_tabs)

	print "i: processing language file"

	for line in fd:
		dharma.parse_line(line)

	print "i: resolving cross-references"

	dharma.resolve_xref()
	dharma.calculate_leaf_paths()

	seed = os.getpid()
	random.seed(seed)
	print "i: using seed " + str(seed)

	print "i: generating output"

	dharma.generate()

	print "i: dharma run complete"

	return

if __name__ == "__main__":
	sys.setrecursionlimit(20000)
	main()
