# coding: utf8
# gen_pos_files.py
#
# Copyright (C) 2018, 2019 Eldar Khayrullin <eldar.khayrullin@mail.ru>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

''' KiCad PCBNew Action Plugin for generating pos files'''

import getpass
import os
import pcbnew
import re
import shutil
import sys
import time

from platform import platform
#from version import VERSION
VERSION = '1.1.0'

OUTPUT_DIR = 'pos'# + os.path.sep + OUTPUT_NAME

EOL = u'\r\n'
SEP = u' '
JSEP = u'_'
EMPTY_FIELD = u'~'
#HEADER = (u'Ref', u'Type', u'Val', u'Type_Val', u'Package', u'PosX', u'PosY',
#          u'Rot', u'Side')
HEADER = (u'Ref', u'Val',  u'Package', u'PosX', u'PosY', u'Rot', u'Side')

REF = 0
VAL = 1
PACKAGE = 2
POSX = 3
POSY = 4
ROT = 5
IS_SMD = 6



IGINOR = ("TestPoint_Probe", "MountingHole_Pad", "Fiducial", "NC", "nc")

TRANSLATE_TABLE = {
    ord(u' ') : u'_',
    ord(u',') : u'.',
    ord(u'¹') : u'^1_',
    ord(u'²') : u'^2_',
    ord(u'³') : u'^3_',
    ord(u'±') : u'+-',

    # russian chars
    ord(u'ё') : u'e',
    ord(u'а') : u'a',
    ord(u'б') : u'b',
    ord(u'в') : u'v',
    ord(u'г') : u'g',
    ord(u'д') : u'd',
    ord(u'е') : u'e',
    ord(u'ж') : u'g',
    ord(u'з') : u'z',
    ord(u'и') : u'i',
    ord(u'й') : u'i',
    ord(u'к') : u'k',
    ord(u'л') : u'l',
    ord(u'м') : u'm',
    ord(u'н') : u'n',
    ord(u'о') : u'o',
    ord(u'п') : u'p',
    ord(u'р') : u'r',
    ord(u'с') : u's',
    ord(u'т') : u't',
    ord(u'у') : u'u',
    ord(u'ф') : u'f',
    ord(u'х') : u'h',
    ord(u'ц') : u'c',
    ord(u'ч') : u'ch',
    ord(u'ш') : u'sh',
    ord(u'щ') : u'ch',
    ord(u'ъ') : u'',
    ord(u'ы') : u'i',
    ord(u'ь') : u'',
    ord(u'э') : u'e',
    ord(u'ю') : u'y',
    ord(u'я') : u'ya',

    ord(u'Ё') : u'E',
    ord(u'А') : u'A',
    ord(u'Б') : u'B',
    ord(u'В') : u'V',
    ord(u'Г') : u'G',
    ord(u'Д') : u'D',
    ord(u'Е') : u'E',
    ord(u'Ж') : u'G',
    ord(u'З') : u'Z',
    ord(u'И') : u'I',
    ord(u'Й') : u'I',
    ord(u'К') : u'K',
    ord(u'Л') : u'L',
    ord(u'М') : u'M',
    ord(u'Н') : u'N',
    ord(u'О') : u'O',
    ord(u'П') : u'P',
    ord(u'Р') : u'R',
    ord(u'С') : u'S',
    ord(u'Т') : u'T',
    ord(u'У') : u'U',
    ord(u'Ф') : u'F',
    ord(u'Х') : u'H',
    ord(u'Ц') : u'C',
    ord(u'Ч') : u'CH',
    ord(u'Ш') : u'SH',
    ord(u'Щ') : u'CH',
    ord(u'Ъ') : u'',
    ord(u'Ы') : u'I',
    ord(u'Ь') : u'',
    ord(u'Э') : u'E',
    ord(u'Ю') : u'Y',
    ord(u'Я') : u'YA',
}


class gen_pos_file(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Generate pos files (SMD+ALL)"
        self.category = "Generates files"
        self.description = "Generates SMD+ALL components pos files"
        self.show_toolbar_button = False # Optional, defaults to False
        #self.icon_file_name = self.get_icon_file_name()

    def Run(self):
        board = pcbnew.GetBoard()
        BoardProcessor().process_board(board)

    def get_icon_file_name(self):
        dirname = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.splitext(os.path.basename(__file__))[0]

        return dirname + os.path.sep + 'bitmaps' + os.path.sep + filename + '.png'


class BoardProcessor():
    def process_board(self, board):
        self.board = board
        self.get_placement_info()
        #self.append_user_fields_to_placement_info()
        #self.conform_fields_to_restrictions()
        self.clean_output(self.get_output_abs_path())
        self.save_placement_info()

    def get_placement_info(self):
        self.placement_info_top = []
        self.placement_info_bottom = []
        self.numALL = 0 
        self.numSMT = 0 
        #components = self.get_components()

        origin = self.board.GetAuxOrigin()

        for module in self.board.GetModules():
            reference = module.GetReference()

            #comp = self.get_component_by_ref(components, reference)
            #if comp:
            #    excluded = (self.get_user_field(comp, u'Исключён из ПЭ') != None)
            #else:
            #    excluded = True
            #if excluded:
            #    continue


            if self.is_non_annotated_ref(reference):
                continue

            value = module.GetValue()
            excluded = False
            for ig in IGINOR:
                if value == ig:
                    excluded = True
            if excluded:
                continue


            
            self.numALL += 1
            package = str(module.GetFPID().GetLibItemName())

            pos = module.GetPosition() - origin

            pos_x = pcbnew.ToMM(pos.x)
            if module.IsFlipped():
                pos_x = -pos_x

            pos_y = -pcbnew.ToMM(pos.y)

            rotation = module.GetOrientationDegrees()

            if module.IsFlipped():
                placement_info = self.placement_info_bottom
            else:
                placement_info = self.placement_info_top

            is_smd = self.is_smd_module(module)
            if is_smd:
                self.numSMT +=1

            placement_info.append([reference, value, package, pos_x, pos_y, rotation, is_smd])

        self.sort_placement_info_by_ref()

    def is_non_annotated_ref(self, ref):
        return ref[-1] == u'*'

    def is_smd_module(self, module):
        attr = module.GetAttributes()
        return (attr == pcbnew.MOD_CMS) or (attr == pcbnew.MOD_VIRTUAL)

    def sort_placement_info_by_ref(self):
        for placement_info in (self.placement_info_top,
                               self.placement_info_bottom):
            placement_info.sort(key=self.get_ref_num)
            placement_info.sort(key=self.get_ref_group)

    def get_ref_group(self, item):
        return re.sub('[0-9]*$', u'', item[REF])

    def get_ref_num(self, item):
        try:
            return int(re.findall('[0-9]*$', item[REF])[0])
        except:
            return 0

    def append_user_fields_to_placement_info(self):
        components = self.get_components()
        for placement_info in (self.placement_info_top,
                               self.placement_info_bottom):
            for item in placement_info:
                comp = self.get_component_by_ref(components, item[REF])
                if comp:
                    type_str = self.get_user_field(comp, u'Марка')
                    if not type_str:
                        type_str = ''
                    if type_str == '':
                        type_str = item[VAL]
                        item[VAL] = ''

                    var_str = self.get_user_field(comp, u'Тип')
                    if not var_str:
                        var_str = ''
                    if var_str != '':
                        type_str += JSEP + var_str

                    type_str = type_str.replace('\\"', '"')

                    accuracy_str = self.get_user_field(comp, u'Класс точности')
                    if not accuracy_str:
                        accuracy_str = ''
                    item[VAL] += accuracy_str
                else:
                    type_str = item[VAL]
                    item[VAL] = ''

                item[TYPE] = type_str

    def get_components(self):
        #name = self.get_board_file_name_without_ext() + u'.sch'
        name = self.get_board_file_name_without_ext() + u'.net'
        print(name)
        return self.get_components_from_sch(name)

    def get_components_from_sch(self, name):
        #components = []
        #sch = kicadsch.Schematic(name)

        net = kicad_netlist_reader.netlist(name)
        components = net.getInterestingComponents()

        return components
#    def get_components_from_sch(self, name):
#        components = []
#        sch = kicadsch.Schematic(name)
#
#        for item in sch.items:
#            if item.__class__.__name__ == u'Comp':
#                # Skip power symbols
#                if not item.fields[0].text.startswith(u'#'):
#                    components.append(item)
#            elif item.__class__.__name__ == u'Sheet':
#                dirname = os.path.dirname(name)
#                filename = os.path.join(dirname, item.file_name)
#                components.extend(self.get_components_from_sch(filename))
#
#        return components
#
    def get_component_by_ref(self, components, ref):
       for comp in components:
           #if self.get_ref_field(comp) == ref:
           if comp.getRef() == ref:
               return comp
       return None

    def get_ref_field(self, comp):
        return comp.fields[0].text

    def get_user_field(self, comp, name):
        #for field in comp.fields:
        for field in comp.getField():
            print(field)
            if hasattr(field, u'name'):
                if field.name == name:
                    return field.text
        return None

    def get_board_file_name_without_ext(self):
        return os.path.splitext(self.board.GetFileName())[0]

    def conform_fields_to_restrictions(self):
        for placement_info in (self.placement_info_top,
                               self.placement_info_bottom):
            for item in placement_info:
                item[TYPE] = self.translate_field(item[TYPE])
                item[VAL] = self.translate_field(item[VAL])
                item[PACKAGE] = self.translate_field(item[PACKAGE])

    def translate_field(self, field):
        if field == '':
            return ''
        else:
            return field.translate(TRANSLATE_TABLE)

    def clean_output(self, path):
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=False, onerror=None)
        os.makedirs(path)

    def save_placement_info(self):
        self.collect_fields_length_statistic()

        shtamp = self.get_shtamp_str()
        path = self.get_output_abs_path()
        name = path + os.path.sep + self.get_board_name()

        pos_file_all = open(name + u'-ALL.pos', mode='w')
        pos_file_smd = open(name + u'-SMD.pos', mode='w')

        pos_file_all.write(shtamp)
        pos_file_smd.write(shtamp)

        total1 = '# Total:' + str(self.numALL) + EOL
        total2 = '# Total:' + str(self.numSMT) + EOL
        pos_file_all.write(total1)
        pos_file_smd.write(total2)

        s = self.get_header_str() + EOL
        pos_file_all.write(s)
        pos_file_smd.write(s)

        self.write_placement_info(pos_file_all, pos_file_smd)

        pos_file_all.close()
        pos_file_smd.close()

    def collect_fields_length_statistic(self):
        self.fields_max_length = []
        for i in range(0, len(HEADER)):
            self.fields_max_length.append(len(HEADER[i]))
        self.fields_max_length[0] += 1

        for placement_info in (self.placement_info_top,
                               self.placement_info_bottom):
            for item in placement_info:
                for field in range(0, len(placement_info[0]) - 1):
                    cur_len = len(str(item[field]))
                    if self.fields_max_length[field] < cur_len:
                        self.fields_max_length[field] = cur_len

    def get_shtamp_str(self):
        return '# Author: ' + getpass.getuser() + \
               ' | Timeshtamp: ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+ \
               ' | Plugin: ' + VERSION + \
               EOL

    def get_output_abs_path(self):
        path = os.path.dirname(os.path.abspath(self.board.GetFileName()))
        return path + os.path.sep + OUTPUT_DIR

    def get_board_name(self):
        name = self.board.GetTitleBlock().GetComment1()
        if name == '':
            name = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
        return name

    def get_header_str(self):
        hlen = len(HEADER) 
        sep_fills = []
        sep_fills.append(self.fields_max_length[REF] - 1 - len(HEADER[0]) + 1)
        sep_fills.append(self.fields_max_length[VAL] - len(HEADER[1]) + 1)
        sep_fills.append(self.fields_max_length[PACKAGE] - len(HEADER[2]) + 1)
        sep_fills.append(self.fields_max_length[POSX] - len(HEADER[3]) + 1)
        sep_fills.append(self.fields_max_length[POSY] - len(HEADER[4]) + 1)
        sep_fills.append(self.fields_max_length[ROT] - len(HEADER[5]) + 1)
        sep_fills.append(0)

        hstr = u'#'
        for i in range(0, hlen):
            hstr += HEADER[i]
            hstr += self.get_separators_str(sep_fills[i])

        return hstr

    def get_separators_str(self, n):
        separators = ''
        for i in range(0, n):
            separators += SEP
        return separators

    def write_placement_info(self, ofile_all, ofile_smd):
        for placement_info in (self.placement_info_top,
                               self.placement_info_bottom):
            is_top = (placement_info is self.placement_info_top)
            if is_top:
                side = u'top'
            else:
                side = u'bottom'

            for item in placement_info:
                self.write_item(item, ofile_all, side)
                if item[IS_SMD]:
                    self.write_item(item, ofile_smd, side)

    def write_item(self, item, ofile, side):
        ofile.write(item[REF])
        num_sep = self.fields_max_length[REF] - len(item[REF]) + 1
        ofile.write(self.get_separators_str(num_sep))

        #ofile.write(item[TYPE])
        #num_sep = self.fields_max_length[TYPE] - len(item[TYPE]) + 1
        #ofile.write(self.get_separators_str(num_sep))

        num_sep = self.fields_max_length[VAL] + 1
        if item[VAL] == '':
            ofile.write(EMPTY_FIELD)
            num_sep -= 1
        else:
            ofile.write(item[VAL])
            num_sep -= len(item[VAL])
        ofile.write(self.get_separators_str(num_sep))

        #ofile.write(item[TYPE])
        #num_sep = self.fields_max_length[TYPE] - len(item[TYPE]) + \
        #          self.fields_max_length[VAL] + len(JSEP) + 1
        #if item[VAL] != '':
        #    ofile.write(JSEP + item[VAL])
        #    num_sep -= len(item[VAL]) + 1
        #ofile.write(self.get_separators_str(num_sep))

        ofile.write(item[PACKAGE])
        num_sep = self.fields_max_length[PACKAGE] - len(item[PACKAGE]) + 1
        ofile.write(self.get_separators_str(num_sep))

        ofile.write(str(item[POSX]))
        num_sep = self.fields_max_length[POSX] - len(str(item[POSX])) + 1
        ofile.write(self.get_separators_str(num_sep))

        ofile.write(str(item[POSY]))
        num_sep = self.fields_max_length[POSY] - len(str(item[POSY])) + 1
        ofile.write(self.get_separators_str(num_sep))

        ofile.write(str(item[ROT]))
        num_sep = self.fields_max_length[ROT] - len(str(item[ROT])) + 1
        ofile.write(self.get_separators_str(num_sep))

        ofile.write(side + EOL)


if __name__ == '__main__':
    board = pcbnew.LoadBoard(sys.argv[1])
    BoardProcessor().process_board(board)
else:
    gen_pos_file().register()
