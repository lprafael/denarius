# Guía para la Obtención del Certificado Digital Tributario (.p12)
**Para Empresas Emisoras de Facturación Electrónica (SIFEN / e-Kuatia)**

Esta guía está destinada a las empresas (contribuyentes) que utilizarán el sistema **Denarius(by Aurelius)** para emitir facturación electrónica en Paraguay. 

Para que la facturación electrónica tenga validez jurídica y sea aceptada por la SET (Marangatu), **cada empresa emisora debe contar con su propio Certificado Digital** que lo identifique legal e inequívocamente ante el Estado.

---

## 1. ¿Qué es el Certificado Digital (.p12)?
Es un archivo informático seguro (usualmente con extensión `.p12` o `.pfx`) que contiene la **Firma Digital** oficial de la empresa. Funciona como el "sello y bolígrafo" legal exclusivo de la compañía para firmar los Documentos Electrónicos (DE).

> **Aclaración Importante:** El certificado es propiedad exclusiva de su empresa (vinculado a su RUC), **no importa qué software de facturación utilice**. Denarius(by Aurelius) actuará únicamente como el motor que utilizará este certificado que usted le proporcione.

## 2. Dónde adquirir el Certificado
En Paraguay, los certificados digitales con validez jurídica tributaria sólo pueden ser emitidos por **Prestadores de Servicios de Certificación (PSC)** autorizados por el Ministerio de Industria y Comercio (MIC). 

Algunas de las prestadoras más utilizadas y recomendadas en el país son:

* **e-Firma (Bancard / Prisma)** - [efirma.com.py](https://www.efirma.com.py/)
* **Code100** - [code100.com.py](https://code100.com.py/)
* **Documenta (Pronet / e-Firma)** 

> **Tip:** Al contactar a cualquiera de estas entidades, debe solicitar específicamente un **"Certificado Digital para Facturación Electrónica (SIFEN / e-Kuatia)"** para Personería Jurídica (o Física, si es unipersonal).

## 3. Requisitos Típicos para la Solicitud
Independientemente de la certificadora que elija, el proceso suele requerir la siguiente documentación escaneada:

**Empresas (Personas Jurídicas):**
1. Constancia de RUC actualizada.
2. Cédula de Identidad (vigente) del Representante Legal.
3. Estatutos de la Sociedad / Escritura de Constitución original inscrita.
4. Acta de Asamblea o Directorio que designe a los representantes actuales.

**Unipersonales (Personas Físicas):**
1. Constancia de RUC actualizada.
2. Cédula de Identidad policial vigente.

## 4. Proceso de Obtención
1. **Contacto y Pre-aprobación:** Póngase en contacto con uno de los PSC mencionados y envié la documentación solicitada.
2. **Pago del Arancel:** Tiene un costo anual, bianual o trianual (varía según la empresa, generalmente a partir de 250.000 a 450.000 Gs. anuales).
3. **Validación de Identidad:** Por normativas de seguridad, el representante legal deberá pasar por un proceso de validación biométrica (suele ser una breve videollamada con un oficial de la certificadora, o presencial).
4. **Entrega y Descarga:** Usted recibirá un enlace seguro y un PIN/Contraseña al correo electrónico registrado. Al ingresar al enlace, el sistema le generará y descargará el archivo `.p12`.

## 5. Pruebas vs Producción (Fase de Homologación)
Antes de facturar a clientes reales, la SET exige un pequeño examen de prueba técnico conocido como **"Homologación"**. 

* **Solicite su certificado de Prueba:** Las certificadoras suelen proveer (a veces sin costo adicional al adquirir el de producción) un certificado exclusivo con motivos de "Homologación / Test". 
* Es con este **Certificado de Pruebas** con el que Denarius(by Aurelius) realizará los tests iniciales ante la SET para habilitar su empresa. 
* Una vez autorizado por la SET, recién ahí se utiliza el **Certificado de Producción** definitivo.

## 6. Siguientes Pasos (Dentro de Denarius(by Aurelius))
Una vez que tenga el archivo **`.p12`** descargado en su computadora y conozca la **contraseña** del mismo, el proceso es simple:

1. Ingrese al panel administrativo de su empresa dentro del sistema **Denarius(by Aurelius)**.
2. Diríjase al apartado de **Configuración > Emisor / Certificados**.
3. Presione **"Cargar Certificado"**.
4. Seleccione el archivo `.p12` que le proveyó la certificadora e introduzca la contraseña estricta que le asignaron.
5. Indíquele a su equipo de desarrollo (Poliverso) que el certificado ya ha sido cargado para que corran el **Motor de Homologación Automatizado**.
