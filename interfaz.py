import PySimpleGUI as sg
import cv2

def main ():
    ##DarkBlue14
    camara = cv2.VideoCapture(0)
    sg.theme('DarkBlue14')

    layout = [[sg.Image(filename='', key='-image-')],
              [sg.Button('Capture', button_color=('white', 'firebrick1')), sg.Button('Exit')]]

    window = sg.Window('Camara',
                       layout,
                       no_titlebar=False,
                       location=(0, 0))

    image_elem = window['-image-']
    numero = 0

    while camara.isOpened():
        #Obtenemos informacion de la interfaz grafica y video
        event, values = window.read(timeout=0)
        ret, frame = camara.read()

        #Si salimos
        if event in ('Exit', None):
            break

        #Si tomamos foto
        elif event == 'Capture':
            cv2.imwrite('c1.png',frame)
        
        if not ret:
            break

        imgbytes = cv2.imencode('.png', frame)[1].tobytes()  # ditto
        image_elem.update(data=imgbytes)
        numero = numero + 1

main()