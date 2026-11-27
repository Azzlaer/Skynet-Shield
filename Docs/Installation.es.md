# Skynet Shield 1.0.0-alpha — instalación de laboratorio

Esta distribución es una versión de pruebas, no un antihack listo para producción. No sustituye ni modifica automáticamente Main.exe, Main.dll o GameServer.exe. No hay sanciones automáticas. Consultar SecurityReview.md para las condiciones de salida.

## 1. Descargar y verificar
En GitHub Actions, abrir una ejecución exitosa de Alpha distribution packages y descargar el artifact. Extraer el contenedor de GitHub y luego el ZIP de Skynet Shield en una carpeta privada. Comparar el SHA-256 del ZIP con el archivo .sha256 mediante Get-FileHash -Algorithm SHA256. SHA256SUMS.txt lista los hashes de los archivos internos. Los hashes detectan corrupción; no son una firma digital ni garantizan autenticidad si ambos archivos fueron alterados. Obtenerlos por un canal confiable.

## 2. Requisitos
Windows 11 x64 recomendado, Python 3.10+ con SQLite, .NET Desktop Runtime 8 x64 (AdminCP no es autocontenido), Microsoft Visual C++ Redistributable 2015-2022 de la arquitectura de cada DLL. Para recompilar: Visual Studio 2022 con C++, CMake 3.21+, SDK .NET 8. Para herramientas de firma de manifiestos, OpenSSL. Ejecutar Deployment/Check-Prerequisites.ps1 desde PowerShell sin privilegios administrativos. El script no descarga dependencias, no comprueba el redistribuible de C++ y solo verifica requisitos básicos.

## 3. Servidor local de desarrollo
Abrir AdminCP/SkynetShield.Admin.exe desde la carpeta raíz extraída, o indicar esa carpeta en Settings > Repository root. En Settings generar claves independientes de desarrollo y configurar Python y ruta SQLite. Iniciar el servidor local desde Server Control; API http://127.0.0.1:8765. Actualizar Dashboard. Las claves se guardan únicamente en memoria de la aplicación; conservarlas mediante un mecanismo privado si se necesitan sesiones entre reinicios. No copiar claves a chats, XML, repositorios ni al cliente.

Alternativamente, establecer SHIELD_ADMIN_KEY y SHIELD_GAME_KEY (64 hex minúsculas, aleatorias e independientes) en el entorno privado del proceso, y ejecutar Deployment/Start-LocalShield.ps1. Para varias instancias copiar Config/ShieldServers.example.xml, asignar las variables privadas indicadas y establecer SHIELD_REGISTRY con su ruta absoluta. AdminCP puede seleccionar ese XML; las claves individuales deben estar en su entorno antes de arrancar. No publicar el servidor wsgiref ni abrir su puerto al exterior.

## 4. Integración MU
Native/x86 contiene las DLL y bibliotecas de importación para los procesos x86; Native/x64 sirve para hosts x64. Common y Bridge contienen headers; Integration contiene adaptadores de referencia. Para el GameServer original, probar primero enlace ABI con v140 y usar ShieldBridge_Login únicamente después de autenticación independiente; ShieldBridge_Logout al cerrar. Ejecutar operaciones en un worker acotado. En Main.dll integrar el adaptador de heartbeat con el código fuente autorizado y entregar el token temporal exclusivamente por un canal autenticado y confidencial. No modificar el ejecutable ni inyectar DLL. La ruta de integración real, renovación y envío nativo de eventos aún no está completada. Leer ShieldBridge.md y MUIntegration.md.

El cliente y el bridge nativos requieren HTTPS con certificado válido. El servidor local HTTP NO satisface ese requisito. Para una prueba TLS controlada, configurar un proxy HTTPS confiable frente al backend privado, con límites de solicitudes y autenticación; el cliente heartbeat usa puerto 443. No desactivar la validación de certificados.

## 5. Actualización y rollback
Detener el servicio y guardar copia de SQLite y configuración privada antes de actualizar. No reemplazar los originales de MU. Conservar el paquete anterior y restaurar copia compatible de la base si es necesario. La migración previa invalida grants antiguos. Revocar o renovar sesiones mediante el ciclo autenticado de la aplicación.

## 6. Validación pendiente
Pruebas reales de Main.dll, GameServer v140, TLS extremo a extremo, GUI interactiva, carga, recuperación y firma de binarios. El paquete incluye un SDK, no una instalación automática de MU. Las pruebas CI no certifican protección contra todos los cheats. No utilizar en producción antes de completar estas validaciones.
