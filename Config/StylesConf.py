class Styles:
    """
    Style snippets for various PyQt objects
    """

    blue_hex = '#006699'
    green_hex = '#8EFA00'
    pink_hex = '#FF2F92'
    orange_hex = '#FF9300'

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

    @staticmethod
    def hex_to_rbg(code: str):
        color = code.lstrip('#')
        return tuple(int(color[i: i + 2], 16) for i in (0, 2, 4))
