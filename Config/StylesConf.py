class Colors:
    """
    Different colors
    """

    # application colors
    app_background = '#333333'
    app_background_lighter = '#444444'
    app_background_event = '#555555'
    app_background_light = '#AAAAAA'
    app_text = '#CCCCCC'

    # cooperate colors
    cooperate_maroon = '#941751'
    cooperate_tu_blue = '#006699'
    cooperate_orange = '#FF9300'
    cooperate_petrol = '#007E71'
    cooperate_violett_darker = '#531B93'
    cooperate_rosa = '#FF818E'
    cooperate_error = '#D6002E'
    cooperate_lime = '#8EFA00'
    cooperate_torquoise = '#00FDFF'
    cooperate_strawberry = '#FF2F92'
    cooperate_violett = '#9E7BFF'
    cooperate_nude = '#FFBFBA'


class Styles:
    """
    Style snippets for various PyQt objects
    """

    global_style_sheet = f'''
        QWidget {{
            background-color: {Colors.app_background};
            color: {Colors.app_text};
        }}

        QPushButton,
        QComboBox,
        QDoubleSpinBox,
        QSpinBox,
        QTabBar::tab {{
            background-color: {Colors.app_background_event};
            border: 1px solid {Colors.app_background_lighter};
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
            background-color: {Colors.app_background_light};
            color: #000000;
        }}
        
        QTableWidget {{
            background-color: {Colors.app_background_lighter};
            color: #FFFFFF;
            border: none;
            gridline-color: {Colors.app_background_event};
        }}
        
        QHeaderView {{   
            color: #000000;
            background-color: {Colors.app_background_light};
        }}
    '''

    title_style_sheet = f'''
        qproperty-alignment: AlignCenter;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        background-color: {Colors.app_background_light};
        padding: 1px 5px;
        margin: 0px;
        color: #000000;
    '''


class Forms:
    """
    Editable form formats
    """

    @staticmethod
    def svgIndicatorLed(color: str) -> str:
        """Returns an Indicator LED svg"""

        return f'''
            <svg height="50px" width="50px" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="lg1">
                        <stop style="stop-color:{color};stop-opacity:1;" offset="0" />
                        <stop style="stop-color:{color};stop-opacity:1;" offset="0.6" />
                        <stop style="stop-color:{color};stop-opacity:0.2;" offset="0.8" />
                        <stop style="stop-color:{color};stop-opacity:0;" offset="1" />
                    </linearGradient>
                    <linearGradient id="lg2">
                        <stop style="stop-color:#FFFFFF;stop-opacity:1;" offset="0" />
                        <stop style="stop-color:#FFFFFF;stop-opacity:0;" offset="1" />
                    </linearGradient>
                    <radialGradient xlink:href="#lg2" id="rg1" cx="20.8" cy="43.2" fx="20.8" fy="43.2" r="0.4" gradientUnits="userSpaceOnUse" gradientTransform="matrix(1.0714285,0,0,1.0714285,-1.4857666,-3.0857145)" />
                    <radialGradient xlink:href="#lg1" id="rg2" cx="20.8" cy="43.2" fx="20.8" fy="43.2" r="0.8" gradientUnits="userSpaceOnUse" />
                </defs>
                <g style="overflow:visible" transform="matrix(31.25,0,0,31.25,-625.0232,-1325)">
                    <path d="M 21.440742,43.2 c 0,0.353281 -0.28672,0.64 -0.64,0.64 -0.35328,0 -0.64,-0.286719 -0.64,-0.64 0,-0.35328 0.28672,-0.64 0.64,-0.64 0.35328,0 0.64,0.28672 0.64,0.64 z" style="overflow:visible;fill:{Colors.app_background_event};fill-opacity:1;stroke:none;stroke-width:0.858442;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1" />
                    <path d="M 21.600742,43.200001 c 0,0.4416 -0.3584,0.799999 -0.8,0.799999 -0.4416,0 -0.8,-0.358399 -0.8,-0.799999 0,-0.441601 0.3584,-0.800001 0.8,-0.800001 0.4416,0 0.8,0.3584 0.8,0.800001 z" style="overflow:visible;fill:url(#rg2);fill-opacity:1;stroke:none;stroke-width:1.07305;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1" />
                    <path d="M 21.280742,43.200001 c 0,0.264959 -0.21504,0.479999 -0.48,0.479999 -0.26496,0 -0.48,-0.21504 -0.48,-0.479999 0,-0.26496 0.21504,-0.480001 0.48,-0.480001 0.26496,0 0.48,0.215041 0.48,0.480001 z" style="overflow:visible;fill:url(#rg1);stroke:none;stroke-width:0.643832;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1" />
                </g>
            </svg>
        '''
