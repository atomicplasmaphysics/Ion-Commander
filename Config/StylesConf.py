class Styles:
    """
    Style snippets for various PyQt objects
    """

    global_style_sheet = f'''
        QWidget {{
            background-color: #333;
            color: #ccc;
        }}

        QPushButton,
        QComboBox,
        QDoubleSpinBox,
        QSpinBox {{
            background-color: #555;
            border: 1px solid #444;
            padding: 3px;
            color: #ccc;
        }}

        QPushButton:hover,
        QComboBox:hover,
        QDoubleSpinBox:hover,
        QSpinBox:hover {{
            background-color: #666;
        }}
        
        QGroupBox {{
            padding: 0px;
            margin: 0px;
        }}
        
        QLabel {{
            background: None;
        }}
    '''


class Colors:
    """
    Different coperate colors
    """

    maroon = '#941751'
    tu_blue = '#006699'
    orange = '#FF9300'
    petrol = '#007E71'
    violett_darker = '#531B93'
    rosa = '#FF818E'
    error = '#D6002E'
    lime = '#8EFA00'
    torquoise = '#00FDFF'
    strawberry = '#FF2F92'
    violett = '#9E7BFF'
    nude = '#FFBFBA'

    @staticmethod
    def hex_to_rbg(code: str):
        color = code.lstrip('#')
        return tuple(int(color[i: i + 2], 16) for i in (0, 2, 4))
