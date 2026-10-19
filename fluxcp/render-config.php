<?php
// Writes FluxCP's application.php and servers.php from the environment,
// starting from the pristine copies, with every value escaped by var_export.
$e = function ($k, $d = null) {
	$v = getenv($k);
	if ($v === false || $v === '') {
		if ($d === null) { fwrite(STDERR, "set $k\n"); exit(1); }
		return $d;
	}
	return $v;
};
$q = fn($v) => var_export($v, true);
$dist = '/opt/fluxcp-config-dist';
$cfg = '/var/www/html/config';

$app = file_get_contents("$dist/application.php");
$app = strtr($app, [
	"'ServerAddress'        => 'localhost'" => "'ServerAddress'        => " . $q($e('FLUXCP_HOST', 'localhost')),
	"'InstallerPassword'    => 'secretpassword'" => "'InstallerPassword'    => " . $q($e('FLUXCP_INSTALLER_PASSWORD')),
	"'SiteTitle'            => 'Flux Control Panel'" => "'SiteTitle'            => " . $q($e('SITE_TITLE', 'Family RO')),
]);
file_put_contents("$cfg/application.php", $app);

$srv = file_get_contents("$dist/servers.php");
$srv = strtr($srv, [
	"'ServerName'     => 'FluxRO'" => "'ServerName'     => " . $q($e('SERVER_NAME', 'Hercules')),
	"'ServerName'      => 'FluxRO'" => "'ServerName'      => " . $q($e('SERVER_NAME', 'Hercules')),
	"'Hostname'   => '127.0.0.1'" => "'Hostname'   => " . $q($e('DB_HOST', 'db')),
	"'Username'   => 'ragnarok'" => "'Username'   => " . $q($e('DB_USER', 'ragnarok')),
	"'Password'   => 'ragnarok'" => "'Password'   => " . $q($e('DB_PASSWORD')),
	"'Database'   => 'ragnarok'" => "'Database'   => " . $q($e('DB_NAME', 'ragnarok')),
	"'Address'  => '127.0.0.1'" => "'Address'  => " . $q($e('LOGIN_HOST', 'login')),
	"'UseMD5'   => true" => "'UseMD5'   => false",
]);
// char and map blocks both say 'Address' => '127.0.0.1': char first, then map
$needle = "'Address'     => '127.0.0.1'";
foreach ([$e('CHAR_HOST', 'char'), $e('MAP_HOST', 'map')] as $host) {
	$i = strpos($srv, $needle);
	if ($i === false) { fwrite(STDERR, "servers.php layout changed\n"); exit(1); }
	$srv = substr_replace($srv, "'Address'     => " . $q($host), $i, strlen($needle));
}
file_put_contents("$cfg/servers.php", $srv);
