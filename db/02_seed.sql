-- =====================================================================
-- SOC-Lite · Datos semilla (demo funcional)
-- Credenciales demo: todas las cuentas usan la contraseña SocLite#2026!
-- El hash se genera en el propio PostgreSQL con pgcrypto (bcrypt, coste 12).
-- =====================================================================
BEGIN;
SET search_path = soc, public;

-- ---------------------------------------------------------------------
-- 1. Roles y permisos
-- ---------------------------------------------------------------------
INSERT INTO roles (code, name, description, is_system) VALUES
 ('admin',      'Administrador',        'Control total de la plataforma y su configuración', TRUE),
 ('soc_manager','Jefe de SOC',          'Supervisa operación, SLA, equipo y reportes de gestión', TRUE),
 ('analyst',    'Analista SOC',         'Triaje, validación e investigación de alertas', TRUE),
 ('auditor',    'Auditor',              'Acceso de solo lectura, incluida la bitácora de auditoría', TRUE),
 ('viewer',     'Directivo / Consulta', 'Consulta de dashboard y reportes, sin operar alertas', TRUE);

INSERT INTO permissions (code, module, action, description) VALUES
 ('alerts:read',       'alerts',    'read',       'Consultar alertas y su detalle'),
 ('alerts:create',     'alerts',    'create',     'Registrar alertas manuales o por API'),
 ('alerts:update',     'alerts',    'update',     'Cambiar estado, severidad y asignación'),
 ('alerts:assign',     'alerts',    'assign',     'Asignar alertas a analistas'),
 ('alerts:suppress',   'alerts',    'suppress',   'Crear y aplicar reglas de supresión'),
 ('triage:read',       'triage',    'read',       'Ver resultados de triaje y evidencias'),
 ('triage:run',        'triage',    'run',        'Solicitar re-triaje a la IA'),
 ('triage:review',     'triage',    'review',     'Validar o corregir el veredicto de la IA'),
 ('incidents:read',    'incidents', 'read',       'Consultar incidentes'),
 ('incidents:create',  'incidents', 'create',     'Abrir incidentes'),
 ('incidents:update',  'incidents', 'update',     'Actualizar investigación y estado'),
 ('incidents:close',   'incidents', 'close',      'Cerrar incidentes con resolución'),
 ('dashboard:read',    'dashboard', 'read',       'Ver dashboard y métricas'),
 ('reports:read',      'reports',   'read',       'Listar reportes generados'),
 ('reports:generate',  'reports',   'generate',   'Generar reportes operacionales y de gestión'),
 ('reports:download',  'reports',   'download',   'Descargar reportes en PDF, Word o Excel'),
 ('users:read',        'users',     'read',       'Listar usuarios'),
 ('users:create',      'users',     'create',     'Crear usuarios'),
 ('users:update',      'users',     'update',     'Editar usuarios y restablecer credenciales'),
 ('users:deactivate',  'users',     'deactivate', 'Desactivar usuarios'),
 ('roles:read',        'roles',     'read',       'Consultar roles y permisos'),
 ('roles:manage',      'roles',     'manage',     'Asignar permisos a roles'),
 ('audit:read',        'audit',     'read',       'Consultar la bitácora de auditoría'),
 ('settings:read',     'settings',  'read',       'Consultar parámetros del sistema'),
 ('settings:manage',   'settings',  'manage',     'Modificar parámetros y políticas SLA');

-- Matriz RBAC declarativa
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
  FROM roles r
  CROSS JOIN permissions p
 WHERE r.code = 'admin'
    OR (r.code = 'soc_manager' AND p.code IN (
        'alerts:read','alerts:create','alerts:update','alerts:assign','alerts:suppress',
        'triage:read','triage:run','triage:review',
        'incidents:read','incidents:create','incidents:update','incidents:close',
        'dashboard:read','reports:read','reports:generate','reports:download',
        'users:read','roles:read','audit:read','settings:read'))
    OR (r.code = 'analyst' AND p.code IN (
        'alerts:read','alerts:create','alerts:update','alerts:assign',
        'triage:read','triage:run','triage:review',
        'incidents:read','incidents:create','incidents:update',
        'dashboard:read','reports:read','reports:generate','reports:download'))
    OR (r.code = 'auditor' AND p.code IN (
        'alerts:read','triage:read','incidents:read','dashboard:read',
        'reports:read','reports:download','users:read','roles:read',
        'audit:read','settings:read'))
    OR (r.code = 'viewer' AND p.code IN (
        'dashboard:read','alerts:read','reports:read','reports:download'));

-- ---------------------------------------------------------------------
-- 2. Usuarios demo
-- ---------------------------------------------------------------------
INSERT INTO users (id, email, full_name, password_hash, role_id, area, mfa_enabled)
SELECT v.id::uuid, v.email::citext, v.full_name,
       crypt('SocLite#2026!', gen_salt('bf', 12)),
       r.id, v.area, v.mfa
  FROM (VALUES
    ('00000000-0000-4000-8000-000000000001','admin@soclite.local','Ana Torres','TI / Seguridad',TRUE, 'admin'),
    ('00000000-0000-4000-8000-000000000002','gerente.soc@soclite.local','Luis Paredes','SOC',TRUE, 'soc_manager'),
    ('00000000-0000-4000-8000-000000000003','analista1@soclite.local','María Quispe','SOC',FALSE,'analyst'),
    ('00000000-0000-4000-8000-000000000004','analista2@soclite.local','Jorge Salas','SOC',FALSE,'analyst'),
    ('00000000-0000-4000-8000-000000000005','auditor@soclite.local','Carla Mendoza','Auditoría interna',FALSE,'auditor'),
    ('00000000-0000-4000-8000-000000000006','directivo@soclite.local','Raúl Bravo','Gerencia general',FALSE,'viewer')
  ) AS v(id, email, full_name, area, mfa, role_code)
  JOIN roles r ON r.code = v.role_code;

-- ---------------------------------------------------------------------
-- 3. Inventario y fuentes
-- ---------------------------------------------------------------------
INSERT INTO assets (id, name, hostname, ip_address, kind, criticality, owner_area, tags) VALUES
 ('10000000-0000-4000-8000-000000000001','Firewall perimetral','fw01','10.0.0.1','firewall','critical','TI','{perimetro,opnsense}'),
 ('10000000-0000-4000-8000-000000000002','Controlador de dominio','srv-dc01','10.0.10.5','server','critical','TI','{ad,identidad}'),
 ('10000000-0000-4000-8000-000000000003','Servidor web','srv-web01','10.0.20.10','server','high','TI','{web,produccion}'),
 ('10000000-0000-4000-8000-000000000004','Base de datos','srv-db01','10.0.20.11','server','critical','TI','{postgres,produccion}'),
 ('10000000-0000-4000-8000-000000000005','Servidor de correo','srv-mail01','10.0.20.12','server','high','TI','{smtp}'),
 ('10000000-0000-4000-8000-000000000006','ERP corporativo','srv-erp01','10.0.20.20','app','high','Administración','{erp,finanzas}'),
 ('10000000-0000-4000-8000-000000000007','Estación Contabilidad','ws-contab-04','10.0.30.44','workstation','medium','Contabilidad','{office}'),
 ('10000000-0000-4000-8000-000000000008','Estación Gerencia','ws-gerencia-02','10.0.30.12','workstation','high','Gerencia','{vip}'),
 ('10000000-0000-4000-8000-000000000009','Gateway VPN','vpn-gw01','10.0.0.2','network','critical','TI','{vpn,remoto}'),
 ('10000000-0000-4000-8000-000000000010','NAS de respaldos','nas-backup01','10.0.40.5','storage','critical','TI','{backup}'),
 ('10000000-0000-4000-8000-000000000011','Cluster Kubernetes','k8s-prod-01','10.0.50.10','cloud','high','TI','{k8s,contenedores}'),
 ('10000000-0000-4000-8000-000000000012','Laptop remota','lt-remota-07','10.0.60.7','workstation','medium','Comercial','{remoto}');

INSERT INTO alert_sources (code, name, kind, endpoint, config) VALUES
 ('wazuh',   'Wazuh Manager',        'hids',     'https://wazuh.local:55000', '{"index":"wazuh-alerts-*","min_level":3}'),
 ('opnsense','OPNsense Firewall',    'firewall', 'https://fw01.local/api',    '{"parser":"suricata-eve"}'),
 ('suricata','Suricata IDS',         'ids',      'tcp://10.0.0.1:514',        '{"ruleset":"ET Open"}'),
 ('manual',  'Registro manual',      'manual',   NULL,                        '{}');

INSERT INTO sla_policies (severity, ack_minutes, resolve_minutes, notify_channel) VALUES
 ('critical', 5,   60,  'slack'),
 ('high',     15,  240, 'slack'),
 ('medium',   60,  1440,'email'),
 ('low',      240, 4320,'email'),
 ('info',     1440,10080,'none');

-- ---------------------------------------------------------------------
-- 4. Alertas (24; ventana de los últimos 7 días)
-- ---------------------------------------------------------------------
INSERT INTO alerts (id, external_id, source_id, asset_id, rule_id, rule_level, severity, status,
                    title, description, src_ip, dst_ip, src_port, dst_port, protocol,
                    username, agent_name, dedup_count, first_seen_at, last_seen_at,
                    raw_payload, mitre_tactic, mitre_technique, created_at, updated_at)
SELECT v.id::uuid, v.ext, s.id, v.asset::uuid, v.rule, v.lvl, v.sev::severity_level,
       v.status::alert_status, v.title, v.descr, v.src::inet, v.dst::inet,
       v.sport, v.dport, v.proto, v.username, v.agent, v.dup,
       now() - v.age::interval, now() - v.age::interval + interval '2 minutes',
       v.payload::jsonb, v.tactic, v.tech,
       now() - v.age::interval, now() - v.age::interval
  FROM (VALUES
  ('00000000-0000-4000-8000-000000000101','wz-88121',1,'10000000-0000-4000-8000-000000000003','5710',10,'high','triaged',
   'Fuerza bruta SSH contra servidor web',
   'Se detectaron 148 intentos fallidos de autenticación SSH en 3 minutos desde una IP externa.',
   '185.220.101.42','10.0.20.10',51234,22,'tcp','root','srv-web01',37,
   '6 days 4 hours','{"rule":{"id":"5710","level":10,"description":"sshd: brute force"},"decoder":{"name":"sshd"},"data":{"srcip":"185.220.101.42","dstuser":"root"}}',
   'Credential Access','T1110'),
  ('00000000-0000-4000-8000-000000000102','wz-88122',1,'10000000-0000-4000-8000-000000000003','5715',12,'critical','escalated',
   'Inicio de sesión SSH exitoso tras fuerza bruta',
   'La IP 185.220.101.42 autenticó correctamente como root 90 segundos después de 148 fallos.',
   '185.220.101.42','10.0.20.10',51234,22,'tcp','root','srv-web01',1,
   '6 days 3 hours','{"rule":{"id":"5715","level":12,"description":"sshd: authentication success after brute force"}}',
   'Initial Access','T1078'),
  ('00000000-0000-4000-8000-000000000103','wz-88130',1,'10000000-0000-4000-8000-000000000002','550',7,'medium','triaged',
   'Modificación de /etc/passwd en controlador de dominio',
   'FIM detectó cambio en el archivo de cuentas fuera de la ventana de mantenimiento.',
   NULL,'10.0.10.5',NULL,NULL,'tcp','svc_backup','srv-dc01',1,
   '5 days 9 hours','{"rule":{"id":"550","level":7,"description":"File integrity monitoring"},"syscheck":{"path":"/etc/passwd","event":"modified"}}',
   'Persistence','T1136'),
  ('00000000-0000-4000-8000-000000000104','wz-88140',1,'10000000-0000-4000-8000-000000000002','5902',8,'high','triaged',
   'Creación de usuario privilegiado fuera de horario',
   'Se creó la cuenta "helpdesk_tmp" y se añadió al grupo Domain Admins a las 02:14.',
   '10.0.30.44','10.0.10.5',49812,445,'tcp','helpdesk','srv-dc01',1,
   '5 days 2 hours','{"rule":{"id":"5902","level":8},"data":{"target_user":"helpdesk_tmp","group":"Domain Admins"}}',
   'Persistence','T1098'),
  ('00000000-0000-4000-8000-000000000105','wz-88155',1,'10000000-0000-4000-8000-000000000004','5402',8,'high','triaged',
   'Escalada de privilegios mediante sudo',
   'El usuario de aplicación ejecutó "sudo -i" sin ticket de cambio asociado.',
   NULL,'10.0.20.11',NULL,NULL,'tcp','appuser','srv-db01',3,
   '4 days 20 hours','{"rule":{"id":"5402","level":8},"data":{"command":"sudo -i"}}',
   'Privilege Escalation','T1548'),
  ('00000000-0000-4000-8000-000000000106','wz-88160',1,'10000000-0000-4000-8000-000000000005','510',13,'critical','escalated',
   'Posible rootkit detectado en servidor de correo',
   'La firma del módulo del kernel no coincide con el catálogo del sistema.',
   NULL,'10.0.20.12',NULL,NULL,'tcp',NULL,'srv-mail01',1,
   '4 days 11 hours','{"rule":{"id":"510","level":13},"data":{"module":"hideproc"}}',
   'Defense Evasion','T1014'),
  ('00000000-0000-4000-8000-000000000107','opn-4412',2,'10000000-0000-4000-8000-000000000003','31103',10,'high','triaged',
   'Intento de inyección SQL en portal web',
   'Petición GET con UNION SELECT y comentarios SQL hacia el parámetro id del portal.',
   '203.0.113.77','10.0.20.10',40122,443,'tcp',NULL,'srv-web01',12,
   '3 days 22 hours','{"rule":{"id":"31103"},"http":{"method":"GET","url":"/producto.php?id=1%20UNION%20SELECT%20user,pass"}}',
   'Initial Access','T1190'),
  ('00000000-0000-4000-8000-000000000108','opn-4418',2,'10000000-0000-4000-8000-000000000003','31105',6,'low','triaged',
   'Intento de Cross-Site Scripting reflejado',
   'Se enviaron etiquetas script en el parámetro de búsqueda. Bloqueado por WAF.',
   '198.51.100.23','10.0.20.10',44810,443,'tcp',NULL,'srv-web01',8,
   '3 days 18 hours','{"http":{"url":"/buscar?q=<script>alert(1)</script>"}}',
   'Execution','T1059'),
  ('00000000-0000-4000-8000-000000000109','opn-4430',2,'10000000-0000-4000-8000-000000000001','1002',6,'medium','suppressed',
   'Escaneo de puertos desde red interna',
   'Un host interno realizó un barrido SYN sobre 1024 puertos del segmento de servidores.',
   '10.0.30.44','10.0.20.0',55000,445,'tcp',NULL,'fw01',54,
   '3 days 10 hours','{"scan":{"ports":1024,"type":"syn"}}',
   'Discovery','T1046'),
  ('00000000-0000-4000-8000-000000000110','wz-88190',1,'10000000-0000-4000-8000-000000000005','52502',12,'critical','escalated',
   'Malware detectado por antivirus en correo',
   'ClamAV identificó "Win.Trojan.Emotet-9" en un adjunto .zip enviado a 3 buzones.',
   NULL,'10.0.20.12',NULL,NULL,'smtp',NULL,'srv-mail01',1,
   '3 days 5 hours','{"rule":{"id":"52502","level":12},"data":{"malware":"Win.Trojan.Emotet-9","file":"factura_2026.zip"}}',
   'Execution','T1204'),
  ('00000000-0000-4000-8000-000000000111','wz-88200',1,'10000000-0000-4000-8000-000000000008','91802',10,'high','triaged',
   'Ejecución de PowerShell ofuscado',
   'Proceso powershell.exe con -enc y cadena Base64 de 4 KB en estación de gerencia.',
   NULL,'10.0.30.12',NULL,NULL,'tcp','rbravo','ws-gerencia-02',1,
   '2 days 23 hours','{"sysmon":{"event":1,"command":"powershell -w hidden -enc SQBFAFgA..."}}',
   'Execution','T1059.001'),
  ('00000000-0000-4000-8000-000000000112','sur-7781',3,'10000000-0000-4000-8000-000000000003','2027865',11,'high','triaged',
   'Consulta DNS hacia dominio de comando y control',
   'Resolución de un dominio incluido en el feed de inteligencia de amenazas (ET Open).',
   '10.0.20.10','8.8.8.8',53122,53,'udp',NULL,'srv-web01',6,
   '2 days 16 hours','{"dns":{"query":"update-sync-cdn.com","rcode":"NOERROR"}}',
   'Command and Control','T1071.004'),
  ('00000000-0000-4000-8000-000000000113','man-0012',4,'10000000-0000-4000-8000-000000000006','MAN-IMT',9,'high','triaged',
   'Viaje imposible en acceso al ERP',
   'Inicio de sesión desde Lima y 8 minutos después desde Rumanía con la misma cuenta.',
   '203.0.113.90',NULL,NULL,443,'tcp','jperez','srv-erp01',1,
   '2 days 9 hours','{"app":"erp","geo":{"login1":"PE","login2":"RO"},"minutes":8}',
   'Initial Access','T1078'),
  ('00000000-0000-4000-8000-000000000114','wz-88210',1,'10000000-0000-4000-8000-000000000002','60122',7,'medium','triaged',
   'Múltiples inicios de sesión fallidos en Windows',
   'Cuenta de servicio con 35 fallos consecutivos; posible contraseña caducada.',
   '10.0.30.44','10.0.10.5',49910,445,'tcp','svc_erp','srv-dc01',35,
   '2 days 2 hours','{"event":{"id":4625,"logon_type":3}}',
   'Credential Access','T1110'),
  ('00000000-0000-4000-8000-000000000115','man-0015',4,'10000000-0000-4000-8000-000000000007','MAN-USB',4,'low','pending',
   'Dispositivo USB no autorizado conectado',
   'Se conectó un almacenamiento USB no inventariado en la estación de contabilidad.',
   NULL,'10.0.30.44',NULL,NULL,'usb','mquispe','ws-contab-04',1,
   '1 day 20 hours','{"device":{"vendor":"SanDisk","serial":"4C530001"}}',
   'Exfiltration','T1052.001'),
  ('00000000-0000-4000-8000-000000000116','opn-4460',2,'10000000-0000-4000-8000-000000000001','FWAUTH',6,'medium','pending',
   'Acceso fallido al panel de administración del firewall',
   'Cinco intentos fallidos de acceso al panel de OPNsense desde la red de invitados.',
   '10.0.70.55','10.0.0.1',38771,443,'tcp','admin','fw01',5,
   '1 day 12 hours','{"app":"opnsense","path":"/index.php"}',
   'Initial Access','T1110'),
  ('00000000-0000-4000-8000-000000000117','man-0021',4,NULL,'MAN-CERT',3,'low','pending',
   'Certificado TLS próximo a expirar',
   'El certificado de la intranet expira en 12 días.',
   NULL,NULL,NULL,443,'tcp',NULL,'srv-web01',1,
   '1 day 4 hours','{"cert":{"cn":"intranet.local","days_left":12}}',
   'Impact','T1499'),
  ('00000000-0000-4000-8000-000000000118','wz-88240',1,'10000000-0000-4000-8000-000000000007','62120',10,'high','pending',
   'Antivirus deshabilitado en estación de trabajo',
   'Windows Defender fue desactivado por política de registro en la estación de contabilidad.',
   NULL,'10.0.30.44',NULL,NULL,'tcp','mquispe','ws-contab-04',1,
   '19 hours','{"registry":{"key":"DisableAntiSpyware","value":1}}',
   'Defense Evasion','T1562.001'),
  ('00000000-0000-4000-8000-000000000119','sur-7802',3,'10000000-0000-4000-8000-000000000002','2034107',10,'high','escalated',
   'Movimiento lateral por SMB',
   'Conexiones SMB administrativas desde una estación a 6 servidores en 2 minutos.',
   '10.0.30.12','10.0.10.5',49820,445,'tcp',NULL,'srv-dc01',6,
   '18 hours','{"smb":{"shares":["ADMIN$","C$"],"hosts":6}}',
   'Lateral Movement','T1021.002'),
  ('00000000-0000-4000-8000-000000000120','sur-7810',3,'10000000-0000-4000-8000-000000000009','2039001',13,'critical','escalated',
   'Túnel DNS compatible con exfiltración de datos',
   'Volumen anómalo de consultas TXT (4,2 MB en 10 minutos) hacia un único dominio.',
   '10.0.60.7','203.0.113.5',53533,53,'udp',NULL,'vpn-gw01',420,
   '11 hours','{"dns":{"qtype":"TXT","bytes_out":4200000,"queries":1813}}',
   'Exfiltration','T1048.003'),
  ('00000000-0000-4000-8000-000000000121','opn-4488',2,'10000000-0000-4000-8000-000000000011','SCAN-EXT',4,'low','false_positive',
   'Escaneo de vulnerabilidades programado',
   'Escaneo autenticado de Tenable ejecutado por el equipo de TI según calendario.',
   '10.0.30.5','10.0.50.10',41000,443,'tcp','svc_scan','k8s-prod-01',1,
   '9 hours','{"scanner":"tenable","schedule":"weekly"}',
   'Discovery','T1595'),
  ('00000000-0000-4000-8000-000000000122','wz-88260',1,'10000000-0000-4000-8000-000000000010','FIM-CRON',7,'medium','pending',
   'Cambio en tarea programada del servidor de respaldos',
   'Se modificó el cron de respaldo; no existe ticket de cambio asociado.',
   NULL,'10.0.40.5',NULL,NULL,'tcp','root','nas-backup01',1,
   '6 hours','{"syscheck":{"path":"/etc/cron.d/backup","event":"modified"}}',
   'Persistence','T1053.003'),
  ('00000000-0000-4000-8000-000000000123','wz-88270',1,'10000000-0000-4000-8000-000000000010','RANSOM-CANARY',14,'critical','pending',
   'Archivo canario de ransomware modificado',
   'El canario del NAS de respaldos fue cifrado; patrón compatible con ransomware.',
   NULL,'10.0.40.5',NULL,NULL,'smb',NULL,'nas-backup01',14,
   '3 hours','{"canary":"/backup/canary.docx","entropy":7.9}',
   'Impact','T1486'),
  ('00000000-0000-4000-8000-000000000124','man-0031',4,'10000000-0000-4000-8000-000000000005','MAN-PHISH',8,'high','triaged',
   'Correo de phishing reportado por usuario',
   'Usuario reportó correo con enlace a formulario de credenciales falso (Microsoft 365).',
   '198.51.100.66','10.0.20.12',NULL,25,'smtp',NULL,'srv-mail01',1,
   '1 hour','{"mail":{"subject":"Actualiza tu contraseña","url":"https://m365-login-secure.example"}}',
   'Initial Access','T1566.002')
  ) AS v(id, ext, source_pos, asset, rule, lvl, sev, status, title, descr, src, dst,
         sport, dport, proto, username, agent, dup, age, payload, tactic, tech)
  JOIN alert_sources s ON s.id = v.source_pos;

-- ---------------------------------------------------------------------
-- 5. Enriquecimiento
-- ---------------------------------------------------------------------
INSERT INTO enrichment_data (alert_id, provider, indicator, indicator_type, verdict, score, raw, ttl_expires_at) VALUES
 ('00000000-0000-4000-8000-000000000101','virustotal','185.220.101.42','ip','malicious',96.00,
  '{"malicious":61,"suspicious":4,"harmless":0,"country":"DE","as_owner":"Hetzner Online GmbH"}', now() + interval '12 hours'),
 ('00000000-0000-4000-8000-000000000101','abuseipdb','185.220.101.42','ip','malicious',100.00,
  '{"abuseConfidenceScore":100,"totalReports":1842,"lastReportedAt":"2026-10-18T22:10:00Z"}', now() + interval '12 hours'),
 ('00000000-0000-4000-8000-000000000101','geoip','185.220.101.42','ip','unknown',NULL,
  '{"country":"DE","city":"Nuremberg","lat":49.45,"lon":11.07}', NULL),
 ('00000000-0000-4000-8000-000000000102','wazuh','rule:5715','rule','malicious',90.00,
  '{"level":12,"groups":["sshd","authentication_success"]}', NULL),
 ('00000000-0000-4000-8000-000000000106','virustotal','hideproc.ko','hash','malicious',88.00,
  '{"sha256":"9f2c...","detections":47,"family":"Linux.Rootkit.XorDDoS"}', now() + interval '24 hours'),
 ('00000000-0000-4000-8000-000000000107','nvd','CVE-2025-42891','cve','malicious',92.00,
  '{"cvss":9.8,"description":"SQL injection en módulo de catálogo","kev":true}', now() + interval '7 days'),
 ('00000000-0000-4000-8000-000000000110','virustotal','factura_2026.zip','hash','malicious',99.00,
  '{"detections":58,"family":"Emotet"}', now() + interval '7 days'),
 ('00000000-0000-4000-8000-000000000111','mitre','T1059.001','technique','malicious',NULL,
  '{"tactic":"execution","name":"PowerShell","url":"https://attack.mitre.org/techniques/T1059/001/"}', NULL),
 ('00000000-0000-4000-8000-000000000112','abuseipdb','8.8.8.8','ip','clean',0.00,
  '{"abuseConfidenceScore":0,"totalReports":2,"usageType":"Public DNS"}', now() + interval '6 hours'),
 ('00000000-0000-4000-8000-000000000113','geoip','203.0.113.90','ip','suspicious',60.00,
  '{"country":"RO","city":"Bucharest","login_anomaly":true}', NULL),
 ('00000000-0000-4000-8000-000000000120','virustotal','update-sync-cdn.com','domain','malicious',84.00,
  '{"malicious":22,"categories":["malware","c2"]}', now() + interval '12 hours'),
 ('00000000-0000-4000-8000-000000000124','urlhaus','https://m365-login-secure.example','url','malicious',95.00,
  '{"threat":"phishing","tags":["m365","credential-harvesting"]}', now() + interval '24 hours'),
 ('00000000-0000-4000-8000-000000000123','wazuh','canary:/backup/canary.docx','file','malicious',99.00,
  '{"entropy_before":4.1,"entropy_after":7.9}', NULL),
 ('00000000-0000-4000-8000-000000000118','wazuh','registry:DisableAntiSpyware','registry','suspicious',75.00,
  '{"gpo":"no-aplica","changed_by":"mquispe"}', NULL),
 ('00000000-0000-4000-8000-000000000109','geoip','10.0.30.44','ip','clean',0.00,
  '{"site":"LAN","segment":"usuarios"}', NULL);

-- ---------------------------------------------------------------------
-- 6. Resultados de triaje (14 alertas procesadas por la IA)
-- ---------------------------------------------------------------------
INSERT INTO triage_results (id, alert_id, model, prompt_version, suggested_severity, verdict,
                            confidence, summary, recommended_actions, mitre_techniques,
                            evidence, tokens_in, tokens_out, latency_ms, cost_usd,
                            needs_human_review, human_verdict, reviewed_by, reviewed_at, created_at)
SELECT v.id::uuid, v.alert::uuid, 'llama3.1:8b-instruct', 'v1.2',
       v.sev::severity_level, v.verdict::triage_verdict, v.conf, v.summary,
       v.actions::jsonb, v.tech::text[], v.evidence::jsonb, v.tin, v.tout, v.ms, v.cost,
       v.review, v.hverdict::triage_verdict, 
       CASE WHEN v.reviewer IS NULL THEN NULL ELSE v.reviewer::uuid END,
       CASE WHEN v.reviewer IS NULL THEN NULL
            ELSE a.created_at + interval '12 minutes' END,
       a.created_at + interval '3 minutes'
  FROM (VALUES
  ('20000000-0000-4000-8000-000000000101','00000000-0000-4000-8000-000000000101','high','true_positive',0.962,
   'IP 185.220.101.42 con 96/100 en VirusTotal y 1.842 reportes en AbuseIPDB ejecutó 148 intentos SSH contra srv-web01 (activo crítico). Patrón consistente con fuerza bruta automatizada; no hay indicios de éxito en esta alerta, pero el volumen y la reputación del origen justifican contención inmediata.',
   '["Bloquear 185.220.101.42 en el firewall perimetral (regla temporal 24 h)","Revisar auth.log de srv-web01 entre 02:00 y 03:00","Verificar si root tiene clave SSH o solo contraseña","Habilitar fail2ban y limitar SSH a la VPN"]',
   '{T1110}', '{"vt_malicious":61,"abuse_score":100,"attempts":148,"asset_criticality":"high"}',
   2840, 512, 4820, 0.000412, TRUE, 'true_positive', '00000000-0000-4000-8000-000000000002', '5 days 20 hours'),
  ('20000000-0000-4000-8000-000000000102','00000000-0000-4000-8000-000000000102','critical','true_positive',0.988,
   'Compromiso confirmado: la misma IP que intentó fuerza bruta autenticó como root 90 segundos después. La secuencia indica éxito de ataque, no un falso positivo. Riesgo de persistencia y movimiento lateral hacia srv-db01.',
   '["Aislar srv-web01 de la red (VLAN de cuarentena)","Rotar credenciales de root y claves SSH","Recolectar memoria y logs forenses antes de reiniciar","Buscar procesos hijos de sshd y conexiones salientes","Abrir incidente crítico y notificar al jefe de SOC"]',
   '{T1110,T1078}', '{"same_ip_as_previous":true,"seconds_between":90,"auth_success":true}',
   3120, 604, 5310, 0.000498, FALSE, NULL, NULL, '5 days 19 hours'),
  ('20000000-0000-4000-8000-000000000103','00000000-0000-4000-8000-000000000103','medium','suspicious',0.741,
   'Cambio en /etc/passwd ejecutado por la cuenta de respaldo. La ventana horaria coincide con la tarea de backup, pero la cuenta no debería modificar archivos de cuentas. Requiere validación con el responsable de TI.',
   '["Comparar /etc/passwd con el respaldo de configuración","Validar si svc_backup tiene permisos de escritura innecesarios","Revisar otros cambios FIM del mismo host"]',
   '{T1136}', '{"path":"/etc/passwd","user":"svc_backup","change_window":"backup"}',
   2210, 388, 4120, 0.000298, TRUE, 'suspicious', '00000000-0000-4000-8000-000000000003', '5 days 8 hours'),
  ('20000000-0000-4000-8000-000000000104','00000000-0000-4000-8000-000000000104','high','true_positive',0.913,
   'Creación de la cuenta helpdesk_tmp y su inclusión en Domain Admins a las 02:14, fuera del horario laboral y sin ticket asociado. Patrón clásico de persistencia con privilegios.',
   '["Deshabilitar helpdesk_tmp y removerla de Domain Admins","Revisar eventos 4720/4728 en el DC","Identificar el origen 10.0.30.44 y su usuario activo","Revisar accesos de las últimas 24 h de la cuenta creada"]',
   '{T1098,T1136}', '{"event_ids":[4720,4728],"hour":"02:14","ticket":null}',
   2560, 442, 4480, 0.000351, FALSE, NULL, NULL, '5 days 1 hour'),
  ('20000000-0000-4000-8000-000000000105','00000000-0000-4000-8000-000000000105','high','suspicious',0.688,
   'Uso de sudo interactivo por la cuenta de aplicación de la base de datos. No se observan comandos destructivos en el evento, pero la cuenta no debería tener shell ni sudo.',
   '["Revisar sudoers y retirar NOPASSWD a appuser","Auditar historial de comandos del usuario","Confirmar con el equipo de aplicaciones si hubo despliegue"]',
   '{T1548}', '{"command":"sudo -i","user":"appuser","ticket":null}',
   1980, 301, 3760, 0.000241, TRUE, NULL, NULL, '4 days 19 hours'),
  ('20000000-0000-4000-8000-000000000106','00000000-0000-4000-8000-000000000106','critical','true_positive',0.954,
   'Módulo de kernel hideproc sin firma válida en srv-mail01. La firma no coincide con el catálogo y el nombre es compatible con rootkits de ocultamiento de procesos. Compromiso de nivel kernel probable.',
   '["Aislar srv-mail01 y preservar evidencia volátil","Analizar módulo con Volatility y comparar hashes","Reinstalar desde imagen base tras contención","Notificar a dirección y evaluar reporte a la autoridad"]',
   '{T1014}', '{"module":"hideproc","signed":false,"vt_family":"Linux.Rootkit.XorDDoS"}',
   3010, 578, 6120, 0.000521, FALSE, NULL, NULL, '4 days 10 hours'),
  ('20000000-0000-4000-8000-000000000107','00000000-0000-4000-8000-000000000107','high','true_positive',0.937,
   'Petición con UNION SELECT y comentarios SQL hacia /producto.php. El WAF registró el intento pero no confirmó explotación exitosa. CVE-2025-42891 (CVSS 9.8, en KEV) afecta el mismo componente.',
   '["Actualizar el módulo de catálogo a la versión parcheada","Revisar logs de aplicación por errores SQL y extracción de datos","Añadir firma WAF específica y bloquear 203.0.113.77","Ejecutar prueba de concepto en entorno de staging"]',
   '{T1190}', '{"cve":"CVE-2025-42891","cvss":9.8,"kev":true,"waf_blocked":true}',
   2740, 498, 5010, 0.000397, FALSE, 'true_positive', '00000000-0000-4000-8000-000000000004', '3 days 21 hours'),
  ('20000000-0000-4000-8000-000000000108','00000000-0000-4000-8000-000000000108','low','false_positive',0.812,
   'Intento de XSS reflejado bloqueado por el WAF y sin ejecución en navegador. El origen es un escáner de cumplimiento autorizado. Riesgo residual bajo.',
   '["Verificar que la respuesta del WAF fue 403","Añadir excepción para el rango del escáner autorizado","Mantener la regla activa para orígenes externos"]',
   '{T1059}', '{"waf_action":"block","scanner_range":true}',
   1720, 244, 2980, 0.000186, FALSE, 'false_positive', '00000000-0000-4000-8000-000000000003', '3 days 17 hours'),
  ('20000000-0000-4000-8000-000000000110','00000000-0000-4000-8000-000000000110','critical','true_positive',0.981,
   'Adjunto factura_2026.zip con Emotet detectado por ClamAV y confirmado en VirusTotal (58 motores). Entregado a 3 buzones del servidor de correo. Riesgo de ejecución por usuarios.',
   '["Cuantificar y borrar el correo de los 3 buzones","Bloquear remitente y hash en el gateway","Escanear las estaciones destinatarias","Notificar a los usuarios afectados"]',
   '{T1204,T1566}', '{"vt_detections":58,"family":"Emotet","recipients":3}',
   2890, 466, 4980, 0.000384, FALSE, NULL, NULL, '3 days 4 hours'),
  ('20000000-0000-4000-8000-000000000111','00000000-0000-4000-8000-000000000111','high','true_positive',0.902,
   'PowerShell con parámetro -enc y carga Base64 de 4 KB ejecutado en la estación de gerencia. La ofuscación y el modo oculto son indicadores de ejecución maliciosa; sin embargo, el usuario reportó haber abierto un documento adjunto.',
   '["Aislar ws-gerencia-02","Volcar la línea de comandos completa y decodificar Base64","Revisar persistencia en Run keys y tareas programadas","Restablecer credenciales del usuario"]',
   '{T1059.001,T1204}', '{"encoded":true,"size_kb":4,"user":"rbravo"}',
   2650, 471, 4590, 0.000374, FALSE, NULL, NULL, '2 days 22 hours'),
  ('20000000-0000-4000-8000-000000000112','00000000-0000-4000-8000-000000000112','medium','suspicious',0.634,
   'Consulta DNS a update-sync-cdn.com, dominio en el feed ET Open. El destino 8.8.8.8 es un resolutor legítimo, por lo que la alerta se centra en el dominio. El host no muestra otras señales de C2.',
   '["Bloquear el dominio en el DNS interno","Revisar el proceso que originó la consulta","Correlacionar con tráfico del mismo host en las últimas 48 h"]',
   '{T1071.004}', '{"domain_age_days":9,"vt_score":84,"host_other_alerts":0}',
   2050, 356, 3880, 0.000279, TRUE, 'suspicious', '00000000-0000-4000-8000-000000000004', '2 days 15 hours'),
  ('20000000-0000-4000-8000-000000000113','00000000-0000-4000-8000-000000000113','high','suspicious',0.777,
   'Acceso al ERP desde Lima y Rumanía con 8 minutos de diferencia para la misma cuenta. Puede deberse a VPN corporativa con salida en el extranjero, pero no hay configuración de ese tipo registrada.',
   '["Contactar al usuario jperez por canal alterno","Revisar logs de VPN y geo-IP de sesiones previas","Forzar cierre de sesiones y cambio de contraseña si no se confirma"]',
   '{T1078,T1133}', '{"country_1":"PE","country_2":"RO","minutes":8,"vpn_exit":false}',
   2310, 402, 4210, 0.000317, TRUE, NULL, NULL, '2 days 8 hours'),
  ('20000000-0000-4000-8000-000000000114','00000000-0000-4000-8000-000000000114','medium','benign',0.856,
   '35 fallos 4625 desde la cuenta de servicio svc_erp, todos desde la misma estación y en un lapso de 2 minutos. Patrón compatible con contraseña caducada y servicio mal configurado, no con ataque.',
   '["Actualizar contraseña del servicio y su almacén de credenciales","Verificar la tarea que usa svc_erp en ws-contab-04","Monitorizar 24 h para descartar persistencia"]',
   '{T1110}', '{"event_id":4625,"same_source":true,"logon_type":3}',
   1840, 289, 3340, 0.000212, FALSE, 'benign', '00000000-0000-4000-8000-000000000003', '2 days 1 hour'),
  ('20000000-0000-4000-8000-000000000124','00000000-0000-4000-8000-000000000124','high','true_positive',0.928,
   'Correo de phishing con enlace a un formulario de credenciales de Microsoft 365, reportado por el usuario. La URL figura en URLhaus como credential-harvesting. No hay evidencia de que se hayan introducido credenciales.',
   '["Bloquear el dominio m365-login-secure.example","Buscar el correo en todos los buzones y eliminarlo","Revisar inicios de sesión de los destinatarios","Enviar recordatorio de concienciación"]',
   '{T1566.002}', '{"urlhaus":"phishing","clicked":false}',
   2190, 377, 4010, 0.000297, FALSE, NULL, NULL, '50 minutes')
  ) AS v(id, alert, sev, verdict, conf, summary, actions, tech, evidence, tin, tout, ms, cost,
         review, hverdict, reviewer, age)
  JOIN alerts a ON a.id = v.alert::uuid;

-- Alineación de estado: las alertas con triaje válido pasan a 'triaged'
UPDATE alerts SET status = 'triaged'
 WHERE status = 'pending'
   AND id IN (SELECT alert_id FROM triage_results);

-- ---------------------------------------------------------------------
-- 7. Incidentes abiertos (5) y su vínculo con alertas
-- ---------------------------------------------------------------------
INSERT INTO incidents (id, code, title, severity, status, asset_id, assigned_to, sla_due_at,
                       opened_at, ticket_system, ticket_ref, created_by) VALUES
 ('30000000-0000-4000-8000-000000000001','INC-2026-00001','Compromiso de servidor web por fuerza bruta SSH',
  'critical','investigating','10000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000003',
  now() - interval '5 days 18 hours', now() - interval '5 days 19 hours','osticket','TCK-1042','00000000-0000-4000-8000-000000000002'),
 ('30000000-0000-4000-8000-000000000002','INC-2026-00002','Posible rootkit en servidor de correo',
  'critical','contained','10000000-0000-4000-8000-000000000005','00000000-0000-4000-8000-000000000004',
  now() - interval '4 days 8 hours', now() - interval '4 days 10 hours','osticket','TCK-1043','00000000-0000-4000-8000-000000000002'),
 ('30000000-0000-4000-8000-000000000003','INC-2026-00003','Malware Emotet en correo corporativo',
  'critical','open','10000000-0000-4000-8000-000000000005','00000000-0000-4000-8000-000000000003',
  now() - interval '2 days 20 hours', now() - interval '3 days 4 hours',NULL,NULL,'00000000-0000-4000-8000-000000000002'),
 ('30000000-0000-4000-8000-000000000004','INC-2026-00004','Exfiltración por túnel DNS desde laptop remota',
  'critical','open','10000000-0000-4000-8000-000000000009','00000000-0000-4000-8000-000000000004',
  now() + interval '45 minutes', now() - interval '11 hours',NULL,NULL,'00000000-0000-4000-8000-000000000001'),
 ('30000000-0000-4000-8000-000000000005','INC-2026-00005','Movimiento lateral por SMB desde estación de gerencia',
  'high','investigating','10000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000003',
  now() + interval '2 hours', now() - interval '18 hours',NULL,NULL,'00000000-0000-4000-8000-000000000002');

INSERT INTO incident_alerts (incident_id, alert_id) VALUES
 ('30000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000102'),
 ('30000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000101'),
 ('30000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000106'),
 ('30000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000110'),
 ('30000000-0000-4000-8000-000000000004','00000000-0000-4000-8000-000000000120'),
 ('30000000-0000-4000-8000-000000000005','00000000-0000-4000-8000-000000000119');

-- Incidentes cerrados del periodo anterior (para MTTR histórico)
INSERT INTO incidents (id, code, title, severity, status, asset_id, assigned_to, sla_due_at,
                       opened_at, closed_at, resolution, ticket_system, ticket_ref, created_by) VALUES
 ('30000000-0000-4000-8000-000000000006','INC-2026-00006','Phishing con robo de credenciales O365',
  'high','closed','10000000-0000-4000-8000-000000000005','00000000-0000-4000-8000-000000000003',
  now() - interval '9 days', now() - interval '10 days', now() - interval '9 days 20 hours',
  'Se bloquearon dominios, se restablecieron 2 contraseñas y se envió comunicación interna.','osticket','TCK-1030','00000000-0000-4000-8000-000000000002'),
 ('30000000-0000-4000-8000-000000000007','INC-2026-00007','Escaneo interno no autorizado',
  'medium','closed','10000000-0000-4000-8000-000000000007','00000000-0000-4000-8000-000000000004',
  now() - interval '12 days', now() - interval '13 days', now() - interval '12 days 6 hours',
  'Era un escaneo de inventario de TI sin ticket; se formalizó el procedimiento.','osticket','TCK-1021','00000000-0000-4000-8000-000000000002');

-- ---------------------------------------------------------------------
-- 8. Supresión, notificaciones y reportes
-- ---------------------------------------------------------------------
INSERT INTO suppression_rules (name, description, match_expr, reason, is_active, created_by) VALUES
 ('Escáner Tenable semanal','Excluye el escaneo autenticado de los domingos 02:00','{"rule_id":"SCAN-EXT","src_ip":"10.0.30.5"}',
  'Actividad autorizada por el calendario de vulnerabilidades', TRUE,'00000000-0000-4000-8000-000000000002'),
 ('Ruido de backup FIM','Cambios esperados del NAS en la ventana 01:00-03:00','{"rule_id":"FIM-CRON","agent_name":"nas-backup01"}',
  'Ventana de respaldo documentada; se revisa semanalmente', FALSE,'00000000-0000-4000-8000-000000000002');

INSERT INTO notifications (alert_id, incident_id, channel, target, subject, payload, status, attempts, sent_at) VALUES
 ('00000000-0000-4000-8000-000000000102','30000000-0000-4000-8000-000000000001','slack','#soc-critical','CRÍTICO: acceso root tras fuerza bruta',
  '{"text":"srv-web01 comprometido","severity":"critical"}','sent',1, now() - interval '5 days 19 hours'),
 ('00000000-0000-4000-8000-000000000106','30000000-0000-4000-8000-000000000002','slack','#soc-critical','CRÍTICO: posible rootkit',
  '{"text":"srv-mail01","severity":"critical"}','sent',1, now() - interval '4 days 10 hours'),
 ('00000000-0000-4000-8000-000000000110','30000000-0000-4000-8000-000000000003','telegram','SOC on-call','CRÍTICO: Emotet en correo',
  '{"text":"3 buzones afectados"}','sent',2, now() - interval '3 days 4 hours'),
 ('00000000-0000-4000-8000-000000000120','30000000-0000-4000-8000-000000000004','slack','#soc-critical','CRÍTICO: exfiltración DNS',
  '{"text":"4,2 MB en 10 min"}','sent',1, now() - interval '11 hours'),
 ('00000000-0000-4000-8000-000000000123',NULL,'telegram','SOC on-call','CRÍTICO: canario ransomware',
  '{"text":"NAS de respaldos"}','failed',3, NULL);

INSERT INTO reports (code, title, kind, format, period_start, period_end, filters, status,
                     generated_by, created_at, completed_at, file_path, file_size) VALUES
 ('RPT-2026-0001','Reporte operacional semanal SOC','operational','pdf',
  CURRENT_DATE - 7, CURRENT_DATE - 1, '{"severity":"all"}','completed',
  '00000000-0000-4000-8000-000000000002', now() - interval '1 day', now() - interval '1 day',
  '/var/soclite/reports/RPT-2026-0001.pdf', 482133),
 ('RPT-2026-0002','Reporte de gestión mensual (KPI y SLA)','management','xlsx',
  date_trunc('month', CURRENT_DATE)::date, CURRENT_DATE, '{}','completed',
  '00000000-0000-4000-8000-000000000002', now() - interval '2 days', now() - interval '2 days',
  '/var/soclite/reports/RPT-2026-0002.xlsx', 92144);

-- ---------------------------------------------------------------------
-- 9. Bitácora de auditoría (12 eventos encadenados)
-- ---------------------------------------------------------------------
-- Los eventos se insertan uno por uno (no en un único INSERT multi-fila) para
-- que el trigger de encadenamiento vea el hash del evento anterior.
DO $$
DECLARE
    e jsonb;
BEGIN
    FOR e IN SELECT jsonb_array_elements($json$
    [
      {"age":"3 days","user_id":"00000000-0000-4000-8000-000000000002","email":"gerente.soc@soclite.local","role":"soc_manager","action":"login","module":"auth","entity":"session","entity_id":null,"result":"success","ip":"10.0.30.12","ua":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","detail":{"method":"password+totp"}},
      {"age":"2 days 23 hours 55 minutes","user_id":"00000000-0000-4000-8000-000000000002","email":"gerente.soc@soclite.local","role":"soc_manager","action":"dashboard.read","module":"dashboard","entity":"kpi","entity_id":null,"result":"success","ip":"10.0.30.12","ua":"Mozilla/5.0","detail":{"period":"7d"}},
      {"age":"2 days 22 hours","user_id":"00000000-0000-4000-8000-000000000003","email":"analista1@soclite.local","role":"analyst","action":"alerts.read","module":"alerts","entity":"alerts","entity_id":null,"result":"success","ip":"10.0.30.44","ua":"Mozilla/5.0","detail":{"filters":{"severity":"critical"}}},
      {"age":"2 days 21 hours 57 minutes","user_id":"00000000-0000-4000-8000-000000000003","email":"analista1@soclite.local","role":"analyst","action":"triage.review","module":"triage","entity":"triage_result","entity_id":"20000000-0000-4000-8000-000000000114","result":"success","ip":"10.0.30.44","ua":"Mozilla/5.0","detail":{"verdict":"benign","note":"contraseña caducada confirmada"}},
      {"age":"2 days 20 hours","user_id":"00000000-0000-4000-8000-000000000004","email":"analista2@soclite.local","role":"analyst","action":"alerts.update","module":"alerts","entity":"alert","entity_id":"00000000-0000-4000-8000-000000000119","result":"success","ip":"10.0.30.45","ua":"Mozilla/5.0","detail":{"from":"pending","to":"escalated"}},
      {"age":"1 day 9 hours","user_id":"00000000-0000-4000-8000-000000000005","email":"auditor@soclite.local","role":"auditor","action":"audit.read","module":"audit","entity":"audit_log","entity_id":null,"result":"success","ip":"10.0.30.60","ua":"Mozilla/5.0","detail":{"range":"30d"}},
      {"age":"1 day 8 hours","user_id":"00000000-0000-4000-8000-000000000006","email":"directivo@soclite.local","role":"viewer","action":"alerts.update","module":"alerts","entity":"alert","entity_id":"00000000-0000-4000-8000-000000000123","result":"denied","ip":"10.0.30.70","ua":"Mozilla/5.0","detail":{"reason":"missing permission alerts:update"}},
      {"age":"1 day 2 hours","user_id":"00000000-0000-4000-8000-000000000002","email":"gerente.soc@soclite.local","role":"soc_manager","action":"reports.generate","module":"reports","entity":"report","entity_id":"RPT-2026-0001","result":"success","ip":"10.0.30.12","ua":"Mozilla/5.0","detail":{"format":"pdf","kind":"operational"}},
      {"age":"20 hours","user_id":"00000000-0000-4000-8000-000000000003","email":"analista1@soclite.local","role":"analyst","action":"alerts.assign","module":"alerts","entity":"alert","entity_id":"00000000-0000-4000-8000-000000000123","result":"success","ip":"10.0.30.44","ua":"Mozilla/5.0","detail":{"assignee":"analista2"}},
      {"age":"12 hours","user_id":"00000000-0000-4000-8000-000000000001","email":"admin@soclite.local","role":"admin","action":"users.update","module":"users","entity":"user","entity_id":"00000000-0000-4000-8000-000000000004","result":"success","ip":"10.0.10.5","ua":"Mozilla/5.0","detail":{"change":"mfa_reset"}},
      {"age":"2 hours","user_id":"00000000-0000-4000-8000-000000000004","email":"analista2@soclite.local","role":"analyst","action":"incidents.update","module":"incidents","entity":"incident","entity_id":"30000000-0000-4000-8000-000000000004","result":"success","ip":"10.0.30.45","ua":"Mozilla/5.0","detail":{"from":"open","to":"investigating"}},
      {"age":"30 minutes","user_id":"00000000-0000-4000-8000-000000000002","email":"gerente.soc@soclite.local","role":"soc_manager","action":"triage.run","module":"triage","entity":"alert","entity_id":"00000000-0000-4000-8000-000000000123","result":"success","ip":"10.0.30.12","ua":"Mozilla/5.0","detail":{"model":"llama3.1:8b-instruct","forced":true}}
    ]
    $json$::jsonb)
    LOOP
        INSERT INTO audit_log (occurred_at, user_id, user_email, role_code, action, module, entity,
                               entity_id, result, ip_address, user_agent, request_id, detail)
        VALUES (
            now() - (e ->> 'age')::interval,
            (e ->> 'user_id')::uuid,
            (e ->> 'email')::citext,
            e ->> 'role',
            e ->> 'action',
            e ->> 'module',
            e ->> 'entity',
            e ->> 'entity_id',
            (e ->> 'result')::audit_result,
            (e ->> 'ip')::inet,
            e ->> 'ua',
            gen_random_uuid(),
            coalesce(e -> 'detail', '{}'::jsonb)
        );
    END LOOP;
END;
$$;

-- ---------------------------------------------------------------------
-- 10. Métricas de los últimos 7 días
-- ---------------------------------------------------------------------
DO $$
DECLARE i INTEGER;
BEGIN
    FOR i IN 1..7 LOOP
        PERFORM fn_refresh_metrics(CURRENT_DATE - i);
    END LOOP;
    PERFORM fn_refresh_metrics(CURRENT_DATE);
END;
$$;

COMMIT;



