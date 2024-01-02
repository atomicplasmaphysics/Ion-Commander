class Styles:
    """
    Style snippets for various PyQt objects
    """

    global_style_sheet = f'''
        QWidget {{
            background-color: #333333;
            color: #CCCCCC;
        }}

        QPushButton,
        QComboBox,
        QDoubleSpinBox,
        QSpinBox,
        QTabBar::tab {{
            background-color: #555555;
            border: 1px solid #444444;
            padding: 3px;
            color: #CCCCCC;
        }}

        QPushButton:hover,
        QComboBox:hover,
        QDoubleSpinBox:hover,
        QSpinBox:hover {{
            background-color: #666666;
        }}
        
        
        QLabel {{
            background: None;
        }}
        
        QTabWidget::pane {{
            border: 0px;
            border-top: 1px solid #CCCCCC;
        }}
        
        QTabBar::tab:selected {{
            background-color: #AAAAAA;
            color: #000000;
        }}
        
        QTableWidget {{
            background-color: #444444;
            color: #FFFFFF;
            border: none;
            gridline-color: #555555;
        }}
        
        QHeaderView {{   
            color: #000000;
            background-color: #AAAAAA;
        }}
    '''

    title_style_sheet = f'''
        qproperty-alignment: AlignCenter;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        background-color: #AAAAAA;
        padding: 1px 5px;
        margin: 0px;
        color: #000000;
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
