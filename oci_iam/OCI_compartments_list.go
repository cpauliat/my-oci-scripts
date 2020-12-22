// --------------------------------------------------------------------------------------------------------------
// This script lists the compartment names and IDs in a OCI tenant using OCI Go SDK
// It will also list all subcompartments
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

// -- main
func main() {
	
	// Check arguments passed
	if (len(os.Args) != 2) { usage() }
	profile := os.Args[1]

	// Try to load OCI config from profile
	config, err := common.ConfigurationProviderFromFileWithProfile(config_file, profile, "")
	client, err := identity.NewIdentityClientWithConfigurationProvider(config)
	helpers.FatalIfError(err)

	// Get info from profile
	tenancy_ocid, _ := config.TenancyOCID()
	user_ocid, _    := config.UserOCID()
	fingerprint, _  := config.KeyFingerprint()
	region, _       := config.Region()

	fmt.Println("OCI profile  = ",profile)
	fmt.Println("Tenancy OCID = ",tenancy_ocid)
	fmt.Println("User OCID    = ",user_ocid)
	fmt.Println("Fingerprint  = ",fingerprint)
	fmt.Println("Region       = ",region)
	fmt.Println("")

	// Get the list of compartments
	vrai := true
	request := identity.ListCompartmentsRequest{ 
		CompartmentId : common.String(tenancy_ocid), 
		CompartmentIdInSubtree : &vrai, 
	}
	list, err := client.ListCompartments(context.Background(), request)
	helpers.FatalIfError(err)

	for i := range list.Items {
		cpt := list.Items[i]
		fmt.Printf("%s, %s, %s\n", *cpt.Name, *cpt.Id, cpt.LifecycleState)	}	
}
