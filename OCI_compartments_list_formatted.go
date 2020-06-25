// --------------------------------------------------------------------------------------------------------------
// This script lists the compartment names and IDs in a OCI tenant using OCI Go SDK
// The output is formatted with colors and indents to easily identify parents of sub-compartments
// Note: OCI tenant given by an OCI CLI PROFILE
// Author        : Christophe Pauliat
// Platforms     : MacOS / Linux
// prerequisites : - Go with OCI SDK installed
//                 - OCI config file configured with profiles
// Versions
//    2020-06-25: Initial Version
// --------------------------------------------------------------------------------------------------------------


package main

// -- import
import (
	"context"
	"fmt"
	"os"

	"github.com/oracle/oci-go-sdk/common"
	"github.com/oracle/oci-go-sdk/identity"
	"github.com/oracle/oci-go-sdk/example/helpers"
)

// -- constants
const config_file string = "~/.oci/config"    // Define config file to be used.
const COLOR_YELLOW = "\033[93m"
const COLOR_RED    = "\033[91m"
const COLOR_GREEN  = "\033[32m"
const COLOR_NORMAL = "\033[39m"
const COLOR_CYAN   = "\033[96m"
const COLOR_BLUE   = "\033[94m"
const COLOR_GREY   = "\033[90m"

// -- global variables
var flag [10]int

// -- functions
func usage() {
    fmt.Printf ("Usage: %s OCI_PROFILE\n",os.Args[0])
    fmt.Println("")
	fmt.Printf ("note: OCI_PROFILE must exist in %s file (see example below)\n",config_file)
	fmt.Println("")
    fmt.Println("[EMEAOSCf]")
    fmt.Println("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    fmt.Println("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    fmt.Println("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    fmt.Println("key_file    = /Users/cpauliat/.oci/api_key.pem")
    fmt.Println("region      = eu-frankfurt-1")
	os.Exit (1)	
}

func get_cpt_name_and_state_from_id(cpt_id string, cpts []identity.Compartment) (string, string) {
	for _, c := range cpts {
        if (*c.Id == cpt_id) {
            return *c.Name, string(c.LifecycleState)
		}
	}
	return "UNKNOWN", "UNKNOWN"
}
	
func display_formatted_list (parent_id string, level int, cpts []identity.Compartment) {
    // level = 0 for root, 1 for 1st level compartments, ...

	var cptname string
	var state string

    for i := 1; i < level; i++ {
        if flag[i] == 0 {
			fmt.Printf (COLOR_CYAN+"│      "+COLOR_NORMAL)
		} else {
            fmt.Printf ("       ")
		}
	}

    if level > 0 {
        cptname, state = get_cpt_name_and_state_from_id (parent_id, cpts)   
        if flag[level] == 0 {
			fmt.Printf (COLOR_CYAN+"├───── "+COLOR_NORMAL)
		} else {
            fmt.Printf (COLOR_CYAN+"└───── "+COLOR_NORMAL)
		}
    } else {
        cptname = "root"
        state   = "ACTIVE"
	}
	
    if state == "ACTIVE" {
		fmt.Println (COLOR_GREEN+cptname+COLOR_NORMAL+" "+parent_id+COLOR_YELLOW+" ACTIVE"+COLOR_NORMAL)
	} else {
        fmt.Println (COLOR_BLUE+cptname+COLOR_GREY+" "+parent_id+COLOR_RED+" DELETED"+COLOR_NORMAL)
	}

	// get the list of ids of the direct sub-compartments and store it in a Go slice
	slice := make([]string,0)
	for _, c := range cpts {
        if (*c.CompartmentId == parent_id) {
            slice = append (slice, *c.Id)
		}
	}
    
    // then for each of those cpt ids, display the sub-compartments details
	for i, cid := range slice {
		// if processing the last sub dir
		if i == len(slice)-1 {
			flag[level+1] = 1
		} else {
			flag[level+1] = 0
		}
		
		// display list of direct sub-folders
		display_formatted_list (cid, level+1, cpts)
	}
}

// -- main
func main() {
	
	// Check arguments passed
	if (len(os.Args) != 2) { usage() }
	profile := os.Args[1]

	// Try to load OCI config from profile
	config, err := common.ConfigurationProviderFromFileWithProfile(config_file, profile, "")
	client, err := identity.NewIdentityClientWithConfigurationProvider(config)
	helpers.FatalIfError(err)

	// Get tenancy OCID from profile
	tenancy_ocid, _ := config.TenancyOCID()

	// Get the list of all compartments and sub-comparments
	vrai := true
	request := identity.ListCompartmentsRequest{ 
		CompartmentId : common.String(tenancy_ocid), 
		CompartmentIdInSubtree : &vrai, 
	}
	list, err := client.ListCompartments(context.Background(), request)
	helpers.FatalIfError(err)

	// Display the list in a formatted output
	display_formatted_list (tenancy_ocid, 0, list.Items)
}
