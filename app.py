#!/usr/bin/python3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import re, os, shutil
import requests
from bs4 import BeautifulSoup as bs
import subprocess


UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['pdf', 'xlsx'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def colorear(valor):
    if valor == 'No':
        return 'color: red'
    elif valor == 'Sí':
        return 'color: green'
    elif valor == '-':
        return 'color: black'
    elif valor == 'Alumno':
        return 'color: black'
    elif valor == 'Socializado':
        return 'color: black'
    else:
        return 'color: red'

# Cruza los ISBN con el fondo comercial y devuelve lista los que no aparecen o tienen alternativa
# Compruba en Imosver si hay nuevo ISBN para las referencias
def isbnNoEnJD(listaIsbnConsulta, listaIsbnEncontrados):

    busquedaImosver = 'https://www.imosver.com/es/busqueda/listaLibros.php?tipoBus=full&palabrasBusqueda='
    resultado = []
    noEstaEnJD = []

    for isbn in listaIsbnConsulta:
        try:
            imosver = requests.get(busquedaImosver + str(isbn))
            soup = bs(imosver.content, 'lxml')
            linkNuevaEdicion = soup.find(class_='nueva_edicion')['href']
            imosver = requests.get('https://www.imosver.com/' + str(linkNuevaEdicion))
            soup = bs(imosver.content, 'lxml')
            nuevoIsbn = soup.select('#summary dd')[4].text
            if isbn not in listaIsbnEncontrados:
                #resultado.append('<font color="red">{}</font> - No está en JDE, se sustituye por - <font color="blue">{}</font> <font color="green"{}</font>'.format(str(isbn), str(nuevoIsbn), soup.find('a', class_='tituloProductoSeo').text))
                noEstaEnJD.append(isbn)
            else:
                resultado.append('<font color="red">{}</font> - Se sustituye por - <font color="blue">{}</font>: <font color="green">{}</font>'.format(str(isbn), str(nuevoIsbn), soup.find('a', class_='tituloProductoSeo').text))
        except:
            if isbn not in listaIsbnEncontrados:
                noEstaEnJD.append(isbn)
                #resultado.append('<font color="red">{}</font> - No está en JDE'.format(str(isbn)))

    # Disponibilidad Imosver
    for isbn in noEstaEnJD:
        try:
            imosver = requests.get(busquedaImosver + str(isbn))
            soup = bs(imosver.content, 'lxml')
            disponibilidad = soup.find('p', class_="muldispo").text
            resultado.append('<font color="red">{}</font> - No está en JDE pero sí en Imosver - <font color="blue">{}</font>'.format(str(isbn), str(disponibilidad)))
        except:
            resultado.append('<font color="red">{}</font> - No está en JDE'.format(str(isbn)))

    return resultado


@app.route("/", methods=["POST", "GET"])
def formulario():

    fondo = pd.read_csv('fondo_v2.csv', sep=';')

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']

            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                    if filename.rsplit('.', 1)[1].lower() == 'pdf':
                        subprocess.call(['pdftohtml', '-c', '-hidden', '-xml', 'uploads/'+filename, 'uploads/salida.xml'])

                        # Lee cadena y borra archivos en uploads/
                        with open('uploads/salida.xml') as f:
                            cadena = f.read()
                        for archivo in os.listdir(UPLOAD_FOLDER):
                            fpath = os.path.join(UPLOAD_FOLDER, archivo)
                            try:
                                if os.path.isfile(fpath):
                                    os.unlink(fpath)
                            except:
                                pass

                    elif filename.rsplit('.', 1)[1].lower() == 'xlsx':
                        os.system("xlsx2csv -s 0 uploads/" + filename + "> uploads/salida.csv")

                        # Lee cadena y borra archivos en uploads/
                        with open('uploads/salida.csv') as f:
                            cadena = f.read()
                        for archivo in os.listdir(UPLOAD_FOLDER):
                            fpath = os.path.join(UPLOAD_FOLDER, archivo)
                            try:
                                if os.path.isfile(fpath):
                                    os.unlink(fpath)
                            except:
                                pass
                else:
                    return render_template('busca_isbn_2.html')
        else:
            cadena = request.form['lista_isbn']

        codigoJD = request.form['codigoCentro']
        nombreColegio = request.form['nombreCentro']
        provincia = request.form['provincia']
        gestor = request.form['gestor']

        listaIsbnConsulta = re.findall(r'9[—.\-\/ ]?7[—.\-\/ ]?8[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d', cadena)
        listaCodigoConsulta = re.findall(r'8[—.\-\/ ]?4[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d[—.\-\/ ]?\d', cadena)

        listaIsbnConsulta.extend(listaCodigoConsulta)

        for i, item in enumerate(listaIsbnConsulta):
            listaIsbnConsulta[i] = re.sub("[^0-9]", "", item)

        fondo_filtrado = fondo[fondo.loc[:, 'ISBN'].isin(listaIsbnConsulta)]

        filas = fondo_filtrado.ISBN.count()

        codigoJD = [codigoJD for item in range(filas)]
        nombreColegio = [nombreColegio for item in range(filas)]
        provincia = [provincia for item in range(filas)]
        gestor = [gestor for item in range(filas)]

        fondo_filtrado['Código JD'] = codigoJD
        fondo_filtrado['Centro'] = nombreColegio
        fondo_filtrado['Provincia'] = provincia
        fondo_filtrado['Gestor'] = gestor

        fondo_filtrado = fondo_filtrado.loc[:, ['ISBN', \
                                                'Editorial', \
                                                'Etapa', \
                                                'Curso', \
                                                'Descripcion del Artículo', \
                                                'Tipo Material', \
                                                'Código JD', \
                                                'Centro', \
                                                'Provincia', \
                                                'Gestor', \
                                                'Comerciable', \
                                                'Catalogación']]
        # Cambia nombre de las columnas
        fondo_filtrado.columns = ['ISBN', \
                                  'Editorial', \
                                  'Etapa', \
                                  'Curso', \
                                  'Descripción', \
                                  'Tipo Material', \
                                  'Código JD', \
                                  'Nombre Colegio', \
                                  'Provincia', \
                                  'Gestor', \
                                  'Comercializable', \
                                  'Catalogación']

        # Remapea columnas
        comercializableSiNo = lambda x: 'Sí' if x == 'COMERCIALIZABLE' else 'No'
        fondo_filtrado.loc[:, 'Comercializable'] = fondo_filtrado['Comercializable'].apply(comercializableSiNo)
        listaIsbnEncontrados = fondo_filtrado.loc[:, 'ISBN'].tolist()
        fondo_filtrado = fondo_filtrado.fillna('-')
        fondo_filtrado.set_index('ISBN', inplace=True)
        fondo_filtrado.index.name = ''
        fondo_filtrado_color = fondo_filtrado.style.applymap(colorear, subset=['Comercializable', 'Catalogación', 'Tipo Material'])
        #tabla = fondo_filtrado.to_html(classes="table table-sm table-striped", index=False, justify='center')
        tabla = fondo_filtrado_color.render(index=False, justify='center').replace('<table id=', '<table class="table table-sm table-striped" id=')
        tabla = tabla.replace('<td id=', '<td align="center" id=')
        tabla = tabla.replace('<th class="blank level0"></th>', '')
        nojd = isbnNoEnJD(listaIsbnConsulta, listaIsbnEncontrados)

        # Si no hay ISBN válidos, no manda la tabla
        if not listaIsbnConsulta:
            tabla = '<h5>Comprueba la lista, no se ha encontrado ningún código ISBN válido...</h5>'
        return  render_template('respuesta_fondo.html', tab=tabla, noJDE=nojd)
    else:
        return render_template('busca_isbn_2.html')


if __name__ == '__main__':
   # fondo = pd.read_csv('g8dqb.csv', sep=';')
    app.run(port = 7777, debug = True)
