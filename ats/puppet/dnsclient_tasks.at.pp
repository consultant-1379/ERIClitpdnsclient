class task_ms1__dnsclient_3a_3anameserver__ms1___2fms_2fconfigs_2fdns__client(){
    dnsclient::nameserver { "ms1_/ms/configs/dns_client":
        name1 => "10.10.10.1",
        name2 => "10.10.10.7",
        name3 => "10.10.10.67",
        search => "exampleone.com exampletwo.com examplethree.com"
    }
}


node "ms1" {

    class {'litp::ms_node':}


    class {'task_ms1__dnsclient_3a_3anameserver__ms1___2fms_2fconfigs_2fdns__client':
    }


}