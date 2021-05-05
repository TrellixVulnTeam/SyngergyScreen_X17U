import pandas as pd
import glob
import string

abc = string.ascii_uppercase


# Here a class (or an object) is made to represent a well on the drug screen plate. This will then be used to aggregate
# data from that well. Most important: what treatment was given and what objects were identified.

class DrugWell:
    def __init__(self, name, plate, row, column, id):
        self.name = name  # well_name is A01 or C06 etc.
        self.id = id
        self.plate = plate  # integers, if multiple plates were used in a drug screen
        self.row = row  # integer, instead of ABC etc.
        self.row_alpha = abc[row]
        self.column = column  # integer
        # below variables are defined to incorporate the drug variables per well. This should be changed if different
        # types of drugs are used.
        self.Lapa = 0
        self.Lapa_unit = "µM"
        self.isin_Lapa = False
        self.Bini = 0
        self.Bini_unit = "µM"
        self.isin_Bini = False
        self.Vino = 0
        self.Vino_unit = "µM"
        self.isin_Vino = False
        self.isin_DMSO = False
        self.Navi = 0
        self.Navi_unit = "µM"
        self.isin_Navi = False
        # identifies plate number in the original file and links it to a known folder that contains the data (csv txt
        # files obtained from Columbus) on these plates.
        self.df_input_path = "input/well_csv/"
        self.df_output_path = "output/well_csv/"
        # the code below fixes a problem that in the columbus export, the 0 before a single digit number is left out,
        # whereas the drug screen uses a 0. Since the drug screen file is the 'basis', the 0 should be removed here to
        # search for the columbus files. Both txt and csv files here are defined, explanation of that choice below.
        if self.column == 1:
            self.file_name_csv = f"*result.{self.name.replace('01', '1[')}*.csv"
        elif self.column < 10:
            self.file_name_csv = f"*result.{self.name.replace('0', '')}*.csv"
        else:
            self.file_name_csv = f"*result.{self.name}*.csv"
        # searches for a file that contains the variables set above. Glob identifies the * as a wildcard variable so
        # it knows to search for patterns instead of literal *.
        self.file_path_get_csv = glob.glob(self.df_input_path + self.file_name_csv)
        self.df = pd.read_csv(self.file_path_get_csv[0], sep=';')
        self.df.rename(columns={"Organoids Selected - Intensity Cell Channel2 Mean": "mean_intensity",
                                          "Organoids Selected - Cell Roundness": "cell_round",
                                          "Organoids Selected - Cell Area [µm²]": "cell_area",
                                          "Organoids Selected - Object No in Organoids": "object_no"}, inplace=True)
        self.total_cells = len(self.df)
        self.roundness_mean = self.df.cell_round.mean()
        self.df.to_csv(f"{self.df_output_path}{self.name}_organoids.csv", sep=';')


    # this method is used to import drug information from the drug printer export into the drug
    # well class.
    # the xml file from the drug printer has a new row for every drug and multiple rows per well.
    def update_drugs(self, name, concentration, unit):
        if name == "Lapatinib":
            self.Lapa = concentration
            self.Lapa_unit = unit
            self.isin_Lapa = True
            self.isin_DMSO = False
        elif name == "Binimetinib":
            self.Bini = concentration
            self.Bini_unit = unit
            self.isin_Bini = True
            self.isin_DMSO = False
        elif name == "Vinorelbine":
            self.Vino = concentration
            self.Vino_unit = unit
            self.isin_Vino = True
            self.isin_DMSO = False
        elif name == "Navitoclax":
            self.Navi = concentration
            self.Navi_unit = unit
            self.isin_Navi = True
            self.isin_DMSO = False
        # the drug printer xml file contains a 'dmso normalization' in all wells as a last row for that well.
        # the step below registers if
        elif name == "DMSO normalization":
            if not self.isin_Lapa and not self.isin_Bini and not self.isin_Vino and not self.isin_Navi:
                self.isin_DMSO = True
            else:
                self.isin_DMSO = False
        else:
            print(f"{name} not defined, please refer to update_drugs method in the Drug"
                  f"Well class")

    # checks the proportion of objects identified that have a roundness above the cut_off variable.
    # gives a verbose summary of findings which can be shut off by overriding the standard verbose boolean
    # variable.
    def prop_alive(self, cut_off, verbose=False):
        self.death_cells = 0
        for cell in self.df.cell_round:
            if cell < cut_off:
                self.death_cells += 1
        self.death_cells_proportion = self.death_cells / self.total_cells
        if verbose:
            print(f"In {self.name}, {self.death_cells} out of {self.total_cells} are alive. "
                  f"\nProportion = {self.death_cells_proportion}"
                  f"\nMean roundness = {self.roundness_mean}")
        return self.death_cells_proportion

    def summary(self):
        print(f"____summary of well____"
              f"\nThis is well {self.name} of plate {self.plate}"
              f"\nLapa: {str(self.Lapa)}{self.Lapa_unit}"
              f"\nBini: {str(self.Bini)}{self.Bini_unit}"
              f"\nVino: {str(self.Vino)}{self.Vino_unit}"
              f"\nNavi: {str(self.Navi)}{self.Navi_unit}"
              f"\nDMSO: {str(self.isin_DMSO)}")




def fill_library():
    # Below the code actually starts.
    # imports 2 xlsx files: the drug print file and a file with conditions in the test
    # this is dependent on the openpyxl package!
    drug_df = pd.read_excel(r'input/Drugconcentrations_perwell.xlsx')
    cond_df = pd.read_excel(r'input/Conditions_table.xlsx')
    # print(drug_df.columns) # gives the following result:
    # Index(['Plate', 'Dispensed\nwell', 'Dispensed\nrow', 'Dispensed\ncol', 'Fluid',
    #     'Fluid name', 'Cassette', 'Dispense\nhead', 'Start time',
    #     'Dispensed concentration', 'Conc. units', 'Dispensed volume',
    #     'Volume units', 'Total well volume'],
    #     dtype='object')
    # below, two a library is made per plate in the experiment. These will hold the drug
    # well classes based on
    # the name of the well.
    class_dict = {}

    well_id = []
    well_name_lst = []
    row = []
    column = []
    plate = []
    cond_id = []
    Navi = []
    Lapa = []
    Bini = []
    Vino = []
    n_organoids = []
    mean_roundness = []

    # here, the library is filled based on the drug printer file with all the drugs per well in a different row

    for index in drug_df.index:
        well_name = str(drug_df['Dispensed\nwell'][index])
        drug_name = drug_df["Fluid name"][index]
        if well_name in class_dict.keys():
            class_dict[well_name].update_drugs(drug_name, drug_df["Dispensed concentration"][index],
                                           drug_df["Conc. units"][index])
        else:
            class_dict[well_name] = DrugWell(drug_df['Dispensed\nwell'][index], drug_df["Plate"][index],
                                         drug_df["Dispensed\nrow"][index],
                                         drug_df["Dispensed\ncol"][index], index)
            class_dict[well_name].update_drugs(drug_name, drug_df["Dispensed concentration"][index],
                                           drug_df["Conc. units"][index])


# this for loop makes a master table with all conditions and well data combined
    for key in class_dict:
        well_id.append(class_dict[key].id)
        well_name_lst.append(class_dict[key].name)
        row.append(class_dict[key].row)
        column.append(class_dict[key].column)
        plate.append(class_dict[key].plate)
        Navi.append(class_dict[key].Navi)
        Lapa.append(class_dict[key].Lapa)
        Bini.append(class_dict[key].Bini)
        Vino.append(class_dict[key].Vino)
        n_organoids.append(class_dict[key].total_cells)
        mean_roundness.append(class_dict[key].roundness_mean)
        if class_dict[key].isin_DMSO:
            cond_id.append(1)
        elif class_dict[key].isin_Navi:
            if 10.018 < class_dict[key].Navi < 10.019:
                cond_id.append(2)
            else:
                cond_id.append(3)
        elif class_dict[key].isin_Lapa:
            if not class_dict[key].isin_Bini and not class_dict[key].isin_Vino:
                cond_id.append(4)
            elif not class_dict[key].isin_Bini and class_dict[key].isin_Vino:
                cond_id.append(5)
            elif class_dict[key].isin_Bini and not class_dict[key].isin_Vino:
                cond_id.append(8)
            elif class_dict[key].isin_Bini and class_dict[key].isin_Vino:
                if 0.119 < class_dict[key].Vino < 0.1191:
                    cond_id.append(9)
                else:
                    cond_id.append(11)
        elif class_dict[key].isin_Bini:
            if not class_dict[key].isin_Vino:
                cond_id.append(6)
            elif class_dict[key].isin_Vino:
                cond_id.append(7)
        elif class_dict[key].isin_Vino:
            cond_id.append(10)
        else:
            print("Couldn't define condition!")
    exp_dict = {'well_id': well_id,
                'well_name': well_name_lst,
                'row': row,
                'column': column,
                'plate': plate,
                'cond_id': cond_id,
                'Navi': Navi,
                'Lapa': Lapa,
                'Bini': Bini,
                'Vino': Vino,
                'n_organoids': n_organoids,
                'mean_roundness': mean_roundness
                }
    exp_df = pd.DataFrame.from_dict(exp_dict)
    exp_df.to_csv('output/experiment_table.csv', sep=';')

def find_positive(plate, cut_off, verbose=True):
    print("================positive controls================")
    for well in plate:
        if plate[well].DMSO:
            if verbose:
                plate[well].summary()
                plate[well].prop_alive(cut_off)
            else:
                print(f"{plate[well].name}: {plate[well].prop_alive(cut_off, False)}")


def find_negative(plate, cut_off, verbose=True):
    print("================negative controls================")
    for well in plate:
        if not plate[well].Navi == 0:
            if verbose:
                plate[well].summary()
                plate[well].prop_alive(cut_off)
            else:
                print(f"{plate[well].name}: {plate[well].prop_alive(cut_off, False)}")


def find_condition(plate, Lapa=False, Bini=False, Vino=False, Navi=False, DMSO=False, verbose=True):
    variable_list = [Lapa, Bini, Vino, Navi, DMSO]
    mission = []
    for var in variable_list:
        if var:
            mission.append(var)
    if not mission:
        print(f"please name a variable from {variable_list} to use this function")
        return None
    elif len(mission) == 1 and DMSO == True:
        print("================positive controls================")
    elif len(mission) == 1 and Navi == True:
        print("================negative controls================")
    else:
        print(f"=======looking for {mission}=======")
    # for well in plate:
    # for objective in mission:
    # if plate[well].objective != 0:
    # if verbose:
    # plate[well].summary()
    # plate[well].prop_alive(cut_off)
    # else:
    # print(f"{plate[well].name}: {plate[well].prop_alive(cut_off,False)}")


# find_positive(class_dict, 0.75,False)
# find_negative(class_dict, 0.75,False)
# find_condition(class_dict, DMSO=True)
# find_condition(class_dict, Navi=True, Bini=True)
# find_condition(class_dict, Navi=True)
fill_library()
