import warnings


import numpy as np

from PyQt6.QtWidgets import QVBoxLayout


from Utility.Layouts import DoubleSpinBox, SpinBox, ComboBox, InputHBoxLayout


class SimulationCalculator:
    """
    Calculator for simulation output data

    :param file_path: input file path
    :param header_count: number of header lines
    :param delimiter: delimiter of data
    :param mass_idx: index of mass
    """

    def __init__(
        self,
        file_path: str,
        header_count: int = 1,
        delimiter: str = ',',
        mass_idx: int = 0,
        tof_idx: int = 2
    ):
        self.file_path = file_path
        with warnings.catch_warnings():
            warnings.simplefilter(action='ignore', category=UserWarning)
            file_data = np.genfromtxt(file_path, skip_header=header_count, delimiter=delimiter)

        if not len(file_data.shape) == 2:
            raise ValueError(f'File "{self.file_path}" has wrong data format')

        tofs_file = dict()

        for row_data in file_data:
            mass = row_data[mass_idx]
            tofs_mass = tofs_file.get(mass, [])
            tofs_mass.append(row_data[tof_idx])
            tofs_file[mass] = tofs_mass

        self.tofs = dict()
        for mass, tofs in tofs_file.items():
            self.tofs[mass] = np.array(tofs)

        if not len(self.tofs):
            raise ValueError(f'File "{self.file_path}" has no data')

        self.interpolate_masses = np.array(list(self.tofs.keys()))
        self.interpolate_masses = self.interpolate_masses[np.argsort(self.interpolate_masses)]

        self.means = dict()
        self.stds = dict()
        interpolate_tofs = []
        for mass in self.interpolate_masses:
            mean = np.mean(self.tofs[mass])
            self.means[mass] = mean
            self.stds[mass] = np.std(self.tofs[mass])
            interpolate_tofs.append(mean)
        self.interpolate_tofs = np.array(interpolate_tofs)

    def getMass(self, tof: float) -> float:
        """Returns interpolated mass for given tof in [ns]"""
        return float(np.interp(tof / 1000, self.interpolate_tofs, self.interpolate_masses))

    def getTofMean(self, mass: float) -> float:
        """Returns mean of tof for given mass in [u] if mass is in dataset"""
        return self.means.get(mass, -1)

    def getTofStd(self, mass: float) -> float:
        """Returns standard deviation of tof for given mass in [u] if mass is in dataset"""
        return self.stds.get(mass, -1)

    def getTofFwhm(self, mass: float) -> float:
        """Returns fwhm of tof for given mass in [u] if mass is in dataset"""
        std = self.stds.get(mass, -1)
        if std == -1:
            return -1
        return 2 * np.sqrt(2 * np.log(2)) * std


class MassCalculatorVBoxLayout(QVBoxLayout):
    """
    Layout for Mass calculator from simulation data

    :param calculators: dict of calculators with filepath as key
    """

    def __init__(
        self,
        calculators: dict[str, SimulationCalculator] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if calculators is None:
            calculators = dict()
        self.calculators = calculators
        self.split = 0

        # Simulation selection
        self.calculator_paths = []
        self.calculator_files = []

        self.simulation_selection = ComboBox(
            entries=self.calculator_files,
            entries_save=self.calculator_paths,
            tooltips=self.calculator_paths
        )
        self.simulation_selection_layout = InputHBoxLayout(
            'Simulation:',
            self.simulation_selection,
            tooltip='Select simulation input file',
            split=self.split
        )

        self.simulation_selection.currentIndexChanged.connect(self.calculate)
        self.addLayout(self.simulation_selection_layout)

        # Laser offset
        self.laser_offset = DoubleSpinBox(
            default=23.79,
            decimals=4,
            input_range=(0, 1000)
        )
        self.laser_offset_layout = InputHBoxLayout(
            'Laser offset [ns]:',
            self.laser_offset,
            tooltip='Offset of laser peak in experimental data in nanoseconds',
            split=self.split
        )

        self.laser_offset.valueChanged.connect(self.calculate)
        self.addLayout(self.laser_offset_layout)

        # Factor offset
        self.factor_offset = DoubleSpinBox(
            default=1.14,
            decimals=4,
            input_range=(0.01, 10),
        )
        self.factor_offset_layout = InputHBoxLayout(
            'Factor offset:',
            self.factor_offset,
            tooltip='Factor to multiply experimental data with',
            split=self.split
        )

        self.factor_offset.valueChanged.connect(self.calculate)
        self.addLayout(self.factor_offset_layout)

        # TOF
        self.tof = DoubleSpinBox(
            default=0,
            decimals=4,
            input_range=(0, 10000)
        )
        self.tof_layout = InputHBoxLayout(
            'TOF in [ns]:',
            self.tof,
            tooltip='TOF of peak in nanoseconds',
            split=self.split
        )

        self.tof.valueChanged.connect(self.calculate)
        self.addLayout(self.tof_layout)

        # Mass output
        self.mass = DoubleSpinBox(
            default=0,
            decimals=2,
            readonly=True
        )
        self.mass_layout = InputHBoxLayout(
            'Resulting mass in [u]:',
            self.mass,
            tooltip='Resulting mass for given TOF and simulation in atomic mass units',
            split=self.split
        )

        self.addLayout(self.mass_layout)

        self.updateCalculators(self.calculators)
        self.calculate()

    def calculate(self):
        """Calculates mass from given input parameters"""

        calculator = self.calculators.get(self.simulation_selection.getValue(save=True), None)
        if calculator is None:
            return
        mass = calculator.getMass((self.tof.value() - self.laser_offset.value()) * self.factor_offset.value())
        self.mass.setValue(mass)

    def updateCalculators(self, calculators: dict[str, SimulationCalculator]):
        """Updates calculators"""

        self.calculators = calculators
        self.calculator_paths = list(self.calculators.keys())
        self.calculator_files = ['.'.join(cp.split('\\')[-1].split('.')[:-1]) for cp in self.calculator_paths]
        self.simulation_selection.reinitialize(
            entries=self.calculator_files,
            entries_save=self.calculator_paths,
            tooltips=self.calculator_paths
        )
        self.simulation_selection.setCurrentIndex(0)


class TOFCalculatorVBoxLayout(QVBoxLayout):
    """
        Layout for TOF calculator from simulation data

        :param calculators: dict of calculators with filepath as key
        """

    def __init__(
        self,
        calculators: dict[str, SimulationCalculator] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if calculators is None:
            calculators = dict()
        self.calculators = calculators
        self.split = 0

        # Simulation selection
        self.calculator_paths = []
        self.calculator_files = []

        self.simulation_selection = ComboBox(
            entries=self.calculator_files,
            entries_save=self.calculator_paths,
            tooltips=self.calculator_paths
        )
        self.simulation_selection_layout = InputHBoxLayout(
            'Simulation:',
            self.simulation_selection,
            tooltip='Select simulation input file',
            split=self.split
        )

        self.simulation_selection.currentIndexChanged.connect(self.calculate)
        self.addLayout(self.simulation_selection_layout)

        # Laser offset
        self.laser_offset = DoubleSpinBox(
            default=23.79,
            decimals=4,
            input_range=(0, 1000)
        )
        self.laser_offset_layout = InputHBoxLayout(
            'Laser offset [ns]:',
            self.laser_offset,
            tooltip='Offset of laser peak in experimental data in nanoseconds',
            split=self.split
        )

        self.laser_offset.valueChanged.connect(self.calculate)
        self.addLayout(self.laser_offset_layout)

        # Factor offset
        self.factor_offset = DoubleSpinBox(
            default=1.14,
            decimals=4,
            input_range=(0.01, 10),
        )
        self.factor_offset_layout = InputHBoxLayout(
            'Factor offset:',
            self.factor_offset,
            tooltip='Factor to multiply experimental data with',
            split=self.split
        )

        self.factor_offset.valueChanged.connect(self.calculate)
        self.addLayout(self.factor_offset_layout)

        # Mass
        self.mass = SpinBox(
            default=1,
            input_range=(0, 10000)
        )
        self.mass_layout = InputHBoxLayout(
            'Mass in [u]:',
            self.mass,
            tooltip='TOF of peak in nanoseconds',
            split=self.split
        )

        self.mass.valueChanged.connect(self.calculate)
        self.addLayout(self.mass_layout)

        # TOF mean output
        self.tof_mean = DoubleSpinBox(
            default=0,
            decimals=2,
            readonly=True
        )
        self.tof_mean_layout = InputHBoxLayout(
            'Resulting mean of TOF in [ns]:',
            self.tof_mean,
            tooltip='Resulting mean of TOF for given mass and simulation in nanoseconds',
            split=self.split
        )

        self.addLayout(self.tof_mean_layout)

        # TOF fwhm output
        self.tof_fwhm = DoubleSpinBox(
            default=0,
            decimals=2,
            readonly=True
        )
        self.tof_fwhm_layout = InputHBoxLayout(
            'Resulting FWHM of TOF in [ps]:',
            self.tof_fwhm,
            tooltip='Resulting FWHM of TOF for given mass and simulation in picoseconds',
            split=self.split
        )

        self.addLayout(self.tof_fwhm_layout)

        self.updateCalculators(self.calculators)
        self.calculate()

    def calculate(self):
        """Calculates TOF from given input parameters"""

        calculator = self.calculators.get(self.simulation_selection.getValue(save=True), None)
        if calculator is None:
            return
        tof_mean = calculator.getTofMean(self.mass.value()) * 1E3 / self.factor_offset.value() + self.laser_offset.value()
        self.tof_mean.setValue(tof_mean)
        tof_fwhm = calculator.getTofFwhm(self.mass.value()) * 1E6
        self.tof_fwhm.setValue(tof_fwhm)

    def updateCalculators(self, calculators: dict[str, SimulationCalculator]):
        """Updates calculators"""

        self.calculators = calculators
        self.calculator_paths = list(self.calculators.keys())
        self.calculator_files = ['.'.join(cp.split('\\')[-1].split('.')[:-1]) for cp in self.calculator_paths]
        self.simulation_selection.reinitialize(
            entries=self.calculator_files,
            entries_save=self.calculator_paths,
            tooltips=self.calculator_paths
        )
        self.simulation_selection.setCurrentIndex(0)


if __name__ == '__main__':
    import sys
    from os import listdir

    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()

            calculators = dict()
            folder = 'D:\\Simion\\LSD - mit DTs\\mass_sweep'
            files = listdir(folder)
            for file in files:
                path = f'{folder}\\{file}'
                try:
                    calculator = SimulationCalculator(path)
                    calculators[path] = calculator
                except ValueError:
                    pass

            central_widget = QWidget()
            layout = MassCalculatorVBoxLayout()
            #layout = TOFCalculatorVBoxLayout()
            central_widget.setLayout(layout)
            layout.updateCalculators(calculators)
            self.setCentralWidget(central_widget)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
