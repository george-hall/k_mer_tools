#!/nfs/users/nfs_g/gh10/Documents/Code/Python/virtualenvs/venv/bin/python


################################################################################
# Copyright (c) 2015 Genome Research Ltd. 
# 
# Author: George Hall gh10@sanger.ac.uk 
# 
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation; either version 3 of the License, or (at your option) any later 
# version. 
# 
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more 
# details. 
# 
# You should have received a copy of the GNU General Public License along with 
# this program. If not, see <http://www.gnu.org/licenses/>. 
################################################################################


import os.path
import sys
import subprocess32
import random
import argparse
import imp

import matplotlib
import matplotlib.pyplot as plt

import scripts.parse_dat_to_histo as parse_data
import settings.graph_settings as graph_settings


def simulate_reads(reference, coverage, read_length, insert_size):
	name = reference.split("/")[-1].split(".")[0]
	subprocess32.call(['sh', '/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/sim_reads.sh', reference, str(coverage), str(read_length), str(insert_size), name])

	return


def update_assembly_config(new_location):
	config_location = "/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/assembly_config"
	with open(config_location, 'r') as assembly_config:
		lines = assembly_config.readlines()
	lines[10] = new_location
	with open(config_location, 'w') as assembly_config:
		assembly_config.writelines(lines)

	return


def process_peak(file_path, file_name, lower_limit, upper_limit, peak_number, reference_path):
	subprocess32.call(['sh', '/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/compute_k_mer_words.sh', file_name, str(lower_limit), str(upper_limit), str(peak_number)]) 
	if reference_path != "":
		subprocess32.call(['sh', '/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/align_sim_to_ref.sh', str(peak_number), file_name, reference_path])
		
		# Assemble repeats:
		new_location = "q=" + os.path.abspath(file_path).split(".")[0] + "_reads/peak_" + str(peak_number) + "_k_mers-read.fastq\n"
		update_assembly_config(new_location)
		subprocess32.call(['sh', '/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/assemble_repeats.sh', os.path.abspath(reference_path), os.path.abspath(file_path), str(peak_number)])

	return


def find_repeats(hist_dict, file_path, num_peaks_desired, reference_path = ""):
	
	"""
	Finds distinct peaks of k-mer spectrum, then uses Smalt to discover k-mer words associated
	with each peak (i.e. which occur within an interval half the width of the peak wither side
	of the peak. The genetic location of these words are then stored. 
	"""

	file_name = file_path.split("/")[-1]
	minima = [minimum[0] for minimum in calculate_mins(hist_dict, num_peaks_desired + 1)]
	maxima = [mode[0] for mode in calculate_modes(hist_dict, num_peaks_desired + 1)]
	intervals = [(y - x) for (x, y) in zip([m for m in minima], [m for m in minima[1:]])] 
	# This assumes that modes don't occur very close to window boundaries:
	peak_ranges = [((m - (i/4)), (m + (i/4))) for (m, i) in zip(maxima, intervals)]

	for (peak_number, (lower_limit, upper_limit)) in enumerate(peak_ranges[1:], 2):
		print "Started processing peak number" , peak_number
		process_peak(file_path, file_name, lower_limit, upper_limit, peak_number, reference_path)
		print "Finished processing peak number" , peak_number

	if reference_path != "":	
		# 'Shred' reference and map to itself (to find all repeats for testing purposes):
		update_assembly_config("q=" + os.path.abspath(reference_path) + "\n")
		subprocess32.call(['sh', '/nfs/users/nfs_g/gh10/Documents/Repositories/k_mer_tools/src/scripts/ssaha_shred.sh', os.path.abspath(reference_path), file_name.split(".")[0]])

	return 

		
def find_extrema(hist_dict, window_size = 50, alternate = False):
	
	"""
	Returns a dict with 2 keys (max and min) with the values for each of these keys being 
	tuples which correspond (occurrence, frequency) pairs which are either a maximum or a 
	minimum.
	"""
	
	i,j,k = (window_size), (window_size + 1), (window_size + 2)
	store_dict = {'Max' : [], 'Min' : []}

	if alternate == False:

		while k < (hist_dict.keys()[-1] - window_size + 1):
			if (all(hist_dict[i - x] <= hist_dict[j] >= hist_dict[k + x] \
			for x in xrange(0, window_size))):
				store_dict['Max'].append((j, hist_dict[j]))
			
			if (all(hist_dict[i - x] >= hist_dict[j] <= hist_dict[k + x] \
			for x in xrange(0, window_size))):
				store_dict['Min'].append((j, hist_dict[j]))
	
			i += 1
			j += 1
			k += 1
			
	else:	
		prev_min, prev_max = False, False
		
		while k < (hist_dict.keys()[-1] - window_size + 1):
			if prev_max == False and (all(hist_dict[i - x] <= hist_dict[j] >= hist_dict[k + x] \
			for x in xrange(0, window_size))):
				store_dict['Max'].append((j,hist_dict[j]))
				prev_min, prev_max = False, True
			
			elif prev_min == False and (all(hist_dict[i - x] >= hist_dict[j] <= hist_dict[k + x] \
			for x in xrange(0, window_size))):			
				store_dict['Min'].append((j,hist_dict[j]))
				prev_min, prev_max = True, False
		
			i += 1
			j += 1
			k += 1

	return store_dict
	
	
def calculate_modes(hist_dict, n):
	"""Takes a hist_dict as input and returns a list containing its first n modes. """
	hist_dict_augmented = pad_data(hist_dict)
	modes = []
	window_size = 50 
	
	while len(modes) < n: # Decrease window size until appropriately small
		modes = []
		for x in sorted(find_extrema(hist_dict_augmented, window_size, 
		alternate = True)['Max'], key = lambda pair: pair[0]):
			if len(modes) < n:
				modes.append(x)
			else:
				break
		window_size = window_size - 5

	return modes
	
	
def calculate_mins(hist_dict, n):
	"""Takes a hist_dict as input and returns a list containing its first n modes. """
	hist_dict_augmented = pad_data(hist_dict)
	mins = []
	window_size = 50

	while len(mins) < n: # Decrease window size until appropriately small
		mins = []
		for x in sorted(find_extrema(hist_dict_augmented, window_size, 
		alternate = True)['Min'], key = lambda pair: pair[0]):
			if len(mins) < n:
				mins.append(x)
			else:
				break
		window_size = window_size - 5

	return mins
	
	
def pad_data(hist_dict):

	"""
	This function is required when, for example, simulated data is being used, as frequency 
	values are not generated for all occurrence values.	That is, not all points on the 
	x-axis will be used when the graph is plotted. This causes problems when trying to use 
	data points as if they are spaced at unit length along the x-axis. To combat this problem, 
	this function returns a dict which contains frequency values for all x values (most of 
	which could well be 0). This allows the data to be used in the correct manner. 
	"""

	for i in xrange(sorted(hist_dict.keys())[0], sorted(hist_dict.keys())[-1]):
		hist_dict.setdefault(i,0)	
	return hist_dict


def compute_genome_size(hists_dict):

	genome_size_list = []
	for size in hists_dict.keys():
		modes = calculate_modes(hists_dict[size], 1)
		
 		# genome_size = total num of k-mer words / first mode of occurences
		genome_size = compute_num_kmer_words(hists_dict[size]) / modes[0][0]
		genome_size_list.append((size, genome_size))
	
	return genome_size_list


def plot_graph(hists_dict, graph_title, use_dots, draw_lines):

	k_mer_sizes = hists_dict.keys()
	for size in k_mer_sizes:
		foo = pad_data(hists_dict[size])
		if not use_dots:
			plt.plot(foo.keys(), foo.values())
		if use_dots:
			plt.plot(foo.keys(), foo.values(), 'o')
		if draw_lines:
			for minimum in calculate_mins(hists_dict[size], 5):
				plt.axvline(minimum[0], c = 'r')
				
	reload(graph_settings)
	settings = graph_settings.generate_settings() 
	
	plt.xlim(settings['x_lower'], settings['x_upper'])
	plt.ylim(settings['y_lower'], settings['y_upper'])
	plt.xscale(settings['x_scale'])
	plt.yscale(settings['y_scale'])
	plt.xlabel(settings['x_label'])
	plt.ylabel(settings['y_label'])

	plt.title(graph_title)
	plt.legend(hists_dict.keys())
	plt.tick_params(labelright = True)

	plt.show()
	
	return


def compute_num_kmer_words(hist_dict):

	total_kmer_words = 0
	total_kmer_words = sum(occurrence * hist_dict[occurrence] for occurrence in hist_dict)
	
	return total_kmer_words
	

def generate_sample(hist_dict, sample_size):
	
	"""
	Generates and returns a sample of size 'sample_size' from 'hist_dict'. Each iteration 
	samples a single occurrence/frequency pair, and stores them in dict 'sample'. This dict 
	is then returned in the same format as a hist_dict.
	""" 
	
	sample = {}
	total_kmer_reads = compute_num_kmer_words(hist_dict)
	
	for i in xrange(sample_size):
		x = random.randint(1,total_kmer_reads)
		iCount = hist_dict[1]
		j = 1
		for j in hist_dict.keys():
			iCount += j * hist_dict[j]
			if iCount > x:
				break
			j += 1
		
		# Increment occurrence frequency count by 1, add occurrence to sample with value 1
		# if previously unobserved
		sample[j] = sample.get(j,0) + 1 
	
	return sample


def compute_hist_from_fast(input_file_path, k_size):
	
	"""
	Uses Jellyfish to count k-mers of length k_size from the file stored at 
	'input_file_path'. This data is stored as a .hgram file in
	/lustre/scratch110/sanger/gh10/Code/k_mer_scripts/hgram_data/. 
	"""

	print "Computing hgram data for k = " + str(k_size) + " for first time"
	print "Reading data for k = " + str(k_size)
	
	file_name = input_file_path.split("/")[-1].split(".")[0]
	mer_count_file = file_name + "_mer_counts.jf"

	# Counts occurences of k-mers of size "k-size" in "file_input":  
	subprocess32.call(["/nfs/users/nfs_g/gh10/src/jellyfish-2.2.3/bin/jellyfish", "count", 
	("-m " + str(k_size)), "-s 1485776702", "-t 25", "-C", input_file_path, 
	'-o', mer_count_file])

	print "Processing histogram for k = " + str(k_size)
	
	file_name = str(input_file_path.split("/")[-1].split(".")[0]) + "_" + str(k_size) + "mer"
	
	with open(file_name + ".hgram","w") as out_file:
		# Computes histogram data and stores in "out_file"
		subprocess32.call(["/nfs/users/nfs_g/gh10/src/jellyfish-2.2.3/bin/jellyfish", "histo", mer_count_file], stdout = out_file)
	
	print "Finished for k = " + str(k_size)
	

def generate_histogram(input_file_path, k_mer_size):
	
	"""
	Essentially ensures that a .hgram file exists and is stored at the correct location for
	the file stored at 'input_file_path'. 
	"""
	
	file_name = input_file_path.split("/")[-1].split(".")[0]
	extension = input_file_path.split("/")[-1].split(".")[-1]
	
	if os.path.isfile(file_name + "_" + str(k_mer_size) + "mer.hgram"):
		return
	
	elif extension in ["data","dat"]:
		parse_data.parse(input_file_path, k_mer_size)
		
	elif extension in ["fasta","fa","fsa","fastq"]:
		if k_mer_size == []:
			raise Exception("Cannot use an empty k-mer size list when trying to create \
			histograms")
		compute_hist_from_fast(input_file_path, k_mer_size)
		
	elif extension == "hgram":
		if str(k_mer_size) == file_name[-len(str(k_mer_size)) - 3:-3]:
			# If file is already histogram with correct k-mer size
			pass
		else:
			raise Exception("Incompatible k-mer size and .hgram file. ")
	
	else:
		raise Exception("Unrecognised file extension. ")


def calculate_hist_dict(input_file_path, k_size):

	"""
	Returns dictionary consisting of keys corresponding to occurrences and values corresponding 
	to frequencies.
	"""
	
	generate_histogram(input_file_path, k_size)
		
	file_name = str(input_file_path.split("/")[-1].split(".")[0]) + "_" + str(k_size) + "mer" 
	extension = str(input_file_path.split("/")[-1].split(".")[-1])
	
	if extension == "hgram":
		hgram_name = input_file_path
	else:
		hgram_name = file_name + ".hgram"
		
	with open(hgram_name, 'r') as hgram_data:

		store_dict = {}
		for line in hgram_data.readlines():
			occ_and_freq = line.split(" ")
			store_dict[int(occ_and_freq[0])] = int(occ_and_freq[1])
	
	return store_dict


def parser():
	
	"""
	Uses argparse module to create an argument parser. This parser's first argument is the
	function which the user wishes to execute, and its second argument is the k-mer sizes
	which the user wishes to use. 
	"""
	
	parser = argparse.ArgumentParser(
	description = "A tool for computing genomic characteristics using k-mers")

	subparsers = parser.add_subparsers(help = "select which function to execute")

	plot_subparser = subparsers.add_parser("plot", help = "plot k-mer spectra")
	plot_subparser.add_argument("path", type = str, help = "location at which the data is stored")
	plot_subparser.add_argument("-o", help = "plot the histogram using red dots", action = "store_true")
	plot_subparser.add_argument("-l", help = "draw lines to split graph into peaks", action = "store_true")
	plot_subparser.add_argument("--graph_title", help = "specify the title for the graph", type = str, default = "")
	plot_subparser.add_argument("k_mer_sizes", help = "k-mer sizes to be used",	type = int, nargs = '+')
	plot_subparser.set_defaults(func = "plot")

	size_subparser = subparsers.add_parser("size", help = "calculate genome size")
	size_subparser.add_argument("path", type = str, help = "location at which the data is stored")
	size_subparser.add_argument("k_mer_sizes", help = "k-mer sizes to be used",	type = int, nargs = '+')
	size_subparser.set_defaults(func = "size")

	repeats_subparser = subparsers.add_parser("repeats", help = "find repetitive k-mer words, and align repetitive contigs to reference")
	repeats_subparser.add_argument("path", type = str, help = "location at which the data is stored")
	repeats_subparser.add_argument("peaks", help = "number of peaks to calculate (first peak calculated will be peak number two)", type = int)
	repeats_subparser.add_argument("k_mer_sizes", help = "k-mer sizes to be used",	type = int, nargs = '+')
	repeats_subparser.add_argument("-ref", help = "location of reference if reads are simulated", type = str, default = "")
	repeats_subparser.set_defaults(func = "repeats")

	indiv_repeats_subparser = subparsers.add_parser("indiv_repeats", help = "find repetitive k-mer words, and align repetitive contigs to reference for a specified range")
	indiv_repeats_subparser.add_argument("path", type = str, help = "location at which the data is stored")
	indiv_repeats_subparser.add_argument("peak_name", type = str, help = "name of peak to be calulated")
	indiv_repeats_subparser.add_argument("l_lim", type = int, help = "lower limit of range")
	indiv_repeats_subparser.add_argument("u_lim", type = int, help = "upper limit of range")
	indiv_repeats_subparser.add_argument("k_mer_sizes", help = "k-mer sizes to be used",	type = int, nargs = '+')
	indiv_repeats_subparser.add_argument("-ref", help = "location of reference if reads are simulated", type = str, default = "")
	indiv_repeats_subparser.set_defaults(func = "indiv_repeats")

	simulate_subparser = subparsers.add_parser("simulate", help = "simulate random reads from reference genome")
	simulate_subparser.add_argument("path", type = str, help = "location at which the data is stored")
	simulate_subparser.add_argument("coverage", type = float, help = "desired simulated coverage")
	simulate_subparser.add_argument("length", type = int, help = "desired simulated read length")
	simulate_subparser.add_argument("insert", type = int, help = "desired simulated insert size")
	simulate_subparser.set_defaults(func = "simulate_reads")

	args = parser.parse_args()
	
	# Dict in which to store k-mer size as key, and hist_dict for that k-mer size as value:
	hists_dict = {}

	# Calculate hists_dict if k_mer_words have been supplied
	try:
		for size in args.k_mer_sizes:
			hists_dict[size] = calculate_hist_dict(args.path, size)
	except AttributeError:
		pass
		
	return (args, hists_dict)

		
def main():

	args, hists_dict = parser()

	if args.func == "plot":
		graph_title = args.graph_title or args.path # If user has entered title then set title
		plot_graph(hists_dict, graph_title, args.o, args.l)

	if args.func == "size":
		print ""
		for size in compute_genome_size(hists_dict):
			print "Size calculated to be " + str(size[1]) + " base pairs (using " + \
			str(size[0]) + "mers)"
			
	if args.func == "repeats":

		extension = ".".join(args.path.split("/")[-1].split(".")[1:])

		if extension not in ["fasta", "fastq"]:
			raise Exception("Incorrect file extension: file must be either .fasta or .fastq")

		file_name = args.path.split("/")[-1].split(".")[0]
		if not os.path.isfile(file_name + "_mer_counts.jf"):
			compute_hist_from_fast(args.path, args.k_mer_sizes[0])

		for size in hists_dict.keys():
			find_repeats(hists_dict[size], args.path, args.peaks, args.ref)
			print "Finished finding repeats"

	if args.func == "indiv_repeats":
# def process_peak(file_path, file_name, lower_limit, upper_limit, peak_number, reference_path):
		extension = ".".join(args.path.split("/")[-1].split(".")[1:])

		if extension not in ["fasta", "fastq"]:
			raise Exception("Incorrect file extension: file must be either .fasta or .fastq")

		file_name = args.path.split("/")[-1].split(".")[0]
		if not os.path.isfile(file_name + "_mer_counts.jf"):
			compute_hist_from_fast(args.path, args.k_mer_sizes[0])

		for size in hists_dict.keys():
			process_peak(args.path, file_name, args.l_lim, args.u_lim, args.peak_name, args.ref)
			print "Finished finding repeats"

	if args.func == "simulate_reads":
		simulate_reads(args.path, args.coverage, args.length, args.insert)

	return


if __name__ == "__main__":
	main()
