define dnsclient::nameserver($name1 = undef, $name2 = undef, $name3 = undef, $search = undef) {
    include "::dnsclient"
    if ($search != ''){
        $mysearch = "search $search\n"
    }
    if ($name1 != ''){
        $myname1 = "nameserver $name1\n"
    }
    if ($name2 != ''){
        $myname2= "nameserver $name2\n"
    }
    if ($name3 != ''){
        $myname3 = "nameserver $name3\n"
    }

    $str = "$mysearch$myname1$myname2$myname3"
    file { "/etc/resolv.conf$name1":
           content => "$str",
           path => "/etc/resolv.conf",
           ensure => file,
     }
}