#!/usr/bin/env python

""" MultiQC module to parse output from HiCUP """

from __future__ import print_function
from collections import OrderedDict
import logging

from multiqc import config, BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='HiCUP', anchor='hicup',
        href='http://www.bioinformatics.babraham.ac.uk/projects/hicup/', 
        info="(Hi-C User Pipeline) is a tool for mapping and performing "\
         "quality control on Hi-C data.")
        
        # Find and load any HiCUP summary reports
        self.hicup_data = dict()
        for f in self.find_log_files(config.sp['hicup']):
            self.parse_hicup_logs(f)

        if len(self.hicup_data) == 0:
            log.debug("Could not find any HiCUP data in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.hicup_data)))
        
        # Write parsed data to a file
        self.write_data_file(self.hicup_data, 'multiqc_hicup')
        
        # Basic Stats Table
        self.hicup_stats_table()
        
        # Report sections
        self.sections = list()
        self.sections.append({
            'name': 'Read Truncation',
            'anchor': 'hicup-truncating',
            'content': self.hicup_truncating_chart()
        })
        self.sections.append({
            'name': 'Read Mapping',
            'anchor': 'hicup-mapping',
            'content': self.hicup_alignment_chart()
        })
        
        self.sections.append({
            'name': 'Read Pair Filtering',
            'anchor': 'hicup-filtering',
            'content': self.hicup_filtering_chart()
        })
        
        # TODO: Is there a log file with this data for a line plot?
        # self.sections.append({
        #     'name': 'Di-Tag Length Distribution',
        #     'anchor': 'hicup-lengths',
        #     'content': self.hicup_lengths_chart()
        # })
        
        self.sections.append({
            'name': 'De-Duplication &amp; Di-Tag Separation',
            'anchor': 'hicup-deduplication',
            'content': self.hicup_dedup_chart()
        })


    def parse_hicup_logs(self, f):
        """ Parse a HiCUP summary report """
        if not f['fn'].endswith('.txt'):
            return None
        header = []
        lines = f['f'].splitlines()
        for l in lines:
            s = l.split("\t")
            if len(header) == 0:
                if s[0] != 'File':
                    return None
                header = s[1:]
            else:
                s_name = self.clean_s_name(s[0], f['root']).lstrip('HiCUP_output/')
                parsed_data = {}
                for idx, num in enumerate(s[1:]):
                    try:
                        parsed_data[header[idx]] = float(num)
                    except:
                        parsed_data[header[idx]] = num
                parsed_data['Duplicate_Read_Pairs'] = parsed_data['Valid_Pairs'] - parsed_data['Deduplication_Read_Pairs_Uniques']
                if s_name in self.hicup_data:
                    log.debug("Duplicate sample name found! Overwriting: {}".format(s_name))
                self.add_data_source(f, s_name)
                self.hicup_data[s_name] = parsed_data


    def hicup_stats_table(self):
        """ Add core HiCUP stats to the general stats table """
        headers = OrderedDict()
        headers['Percentage_Ditags_Passed_Through_HiCUP'] = {
            'title': '% Passed',
            'description': 'Percentage Di-Tags Passed Through HiCUP',
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'YlGn',
            'format': '{:.1f}%',
        }
        headers['Deduplication_Read_Pairs_Uniques'] = {
            'title': 'M Unique',
            'description': 'Unique Di-Tags (millions)',
            'min': 0,
            'scale': 'PuRd',
            'modify': lambda x: x / 1000000,
            'shared_key': 'read_count'
        }
        headers['Percentage_Uniques'] = {
            'title': '% Duplicates',
            'description': 'Percent Duplicate Di-Tags',
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'YlGn-rev',
            'modify': lambda x: 100 - x,
            'format': '{:.1f}%',
        }
        headers['Valid_Pairs'] = {
            'title': 'M Valid',
            'description': 'Valid Pairs (millions)',
            'min': 0,
            'scale': 'PuRd',
            'modify': lambda x: x / 1000000,
            'shared_key': 'read_count'
        }
        headers['Percentage_Valid'] = {
            'title': '% Valid',
            'description': 'Percent Valid Pairs',
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'YlGn',
            'format': '{:.1f}%',
        }
        headers['Paired_Read_1'] = {
            'title': 'M Pairs Aligned',
            'description': 'Paired Alignments (millions)',
            'min': 0,
            'scale': 'PuRd',
            'modify': lambda x: x / 1000000,
            'shared_key': 'read_count'
        }
        headers['Percentage_Mapped'] = {
            'title': '% Aligned',
            'description': 'Percentage of Paired Alignments',
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'YlGn',
            'format': '{:.1f}%',
        }
        self.general_stats_addcols(self.hicup_data, headers, 'HiCUP')
    
    def hicup_truncating_chart (self):
        """ Generate the HiCUP Truncated reads plot """    
        
        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['Not_Truncated_Reads'] = { 'color': '#2f7ed8', 'name': 'Not Truncated' }
        keys['Truncated_Read']      = { 'color': '#0d233a', 'name': 'Truncated' }
        
        # Construct a data structure for the plot - duplicate the samples for read 1 and read 2
        data = {}
        for s_name in self.hicup_data:
            data['{} Read 1'.format(s_name)] = {}
            data['{} Read 2'.format(s_name)] = {}
            data['{} Read 1'.format(s_name)]['Not_Truncated_Reads'] = self.hicup_data[s_name]['Not_Truncated_Reads_1']
            data['{} Read 2'.format(s_name)]['Not_Truncated_Reads'] = self.hicup_data[s_name]['Not_Truncated_Reads_2']
            data['{} Read 1'.format(s_name)]['Truncated_Read'] = self.hicup_data[s_name]['Truncated_Read_1']
            data['{} Read 2'.format(s_name)]['Truncated_Read'] = self.hicup_data[s_name]['Truncated_Read_2']
        
        # Config for the plot
        config = {
            'title': 'HiCUP: Truncated Reads',
            'ylab': '# Reads',
            'cpswitch_counts_label': 'Number of Reads'
        }
        
        return self.plot_bargraph(data, keys, config)
    
    def hicup_alignment_chart (self):
        """ Generate the HiCUP Aligned reads plot """    
        
        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['Unique_Alignments_Read']   = { 'color': '#2f7ed8', 'name': 'Unique Alignments' }
        keys['Multiple_Alignments_Read'] = { 'color': '#492970', 'name': 'Multiple Alignments' }
        keys['Failed_To_Align_Read']     = { 'color': '#0d233a', 'name': 'Failed To Align' }
        keys['Too_Short_To_Map_Read']    = { 'color': '#f28f43', 'name': 'Too short to map' }
        
        # Construct a data structure for the plot - duplicate the samples for read 1 and read 2
        data = {}
        for s_name in self.hicup_data:
            data['{} Read 1'.format(s_name)] = {}
            data['{} Read 2'.format(s_name)] = {}
            data['{} Read 1'.format(s_name)]['Unique_Alignments_Read'] = self.hicup_data[s_name]['Unique_Alignments_Read_1']
            data['{} Read 2'.format(s_name)]['Unique_Alignments_Read'] = self.hicup_data[s_name]['Unique_Alignments_Read_2']
            data['{} Read 1'.format(s_name)]['Multiple_Alignments_Read'] = self.hicup_data[s_name]['Multiple_Alignments_Read_1']
            data['{} Read 2'.format(s_name)]['Multiple_Alignments_Read'] = self.hicup_data[s_name]['Multiple_Alignments_Read_2']
            data['{} Read 1'.format(s_name)]['Failed_To_Align_Read'] = self.hicup_data[s_name]['Failed_To_Align_Read_1']
            data['{} Read 2'.format(s_name)]['Failed_To_Align_Read'] = self.hicup_data[s_name]['Failed_To_Align_Read_2']
            data['{} Read 1'.format(s_name)]['Too_Short_To_Map_Read'] = self.hicup_data[s_name]['Too_Short_To_Map_Read_1']
            data['{} Read 2'.format(s_name)]['Too_Short_To_Map_Read'] = self.hicup_data[s_name]['Too_Short_To_Map_Read_2']
        
        # Config for the plot
        config = {
            'title': 'HiCUP: Mapping Statistics',
            'ylab': '# Reads',
            'cpswitch_counts_label': 'Number of Reads'
        }
        
        return self.plot_bargraph(data, keys, config)
    
    def hicup_filtering_chart(self):
        """ Generate the HiCUP filtering plot """    
        
        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['Valid_Pairs'] =            { 'color': '#2f7ed8', 'name': 'Valid Pairs' }
        keys['Same_Fragment_Internal'] = { 'color': '#0d233a', 'name': 'Same Fragment - Internal' }
        keys['Same_Circularised'] =      { 'color': '#910000', 'name': 'Same Fragment - Circularised' }
        keys['Same_Dangling_Ends'] =     { 'color': '#8bbc21', 'name': 'Same Fragment - Dangling Ends' }
        keys['Re_Ligation'] =            { 'color': '#1aadce', 'name': 'Re-ligation' }
        keys['Contiguous_Sequence'] =    { 'color': '#f28f43', 'name': 'Contiguous Sequence' }
        keys['Wrong_Size'] =             { 'color': '#492970', 'name': 'Wrong Size' }
        
        # Config for the plot
        config = {
            'title': 'HiCUP: Filtering Statistics',
            'ylab': '# Read Pairs',
            'cpswitch_counts_label': 'Number of Read Pairs',
            'cpswitch_c_active': False
        }
        
        return self.plot_bargraph(self.hicup_data, keys, config)
    
    def hicup_dedup_chart(self):
        """ Generate the HiCUP Deduplication plot """    
        
        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['Deduplication_Cis_Close_Uniques'] = { 'color': '#2f7ed8', 'name': 'Unique: cis < 10Kbp' }
        keys['Deduplication_Cis_Far_Uniques']   = { 'color': '#0d233a', 'name': 'Unique: cis > 10Kbp' }
        keys['Deduplication_Trans_Uniques']     = { 'color': '#492970', 'name': 'Unique: trans' }
        keys['Duplicate_Read_Pairs']            = { 'color': '#f28f43', 'name': 'Duplicate read pairs' }
        
        # Config for the plot
        config = {
            'title': 'HiCUP: De-Duplication Statistics',
            'ylab': '# Di-Tags',
            'cpswitch_counts_label': 'Number of Di-Tags',
            'cpswitch_c_active': False
        }
        
        return self.plot_bargraph(self.hicup_data, keys, config)
