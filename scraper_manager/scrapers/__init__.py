"""
Scraper Factory
Import and instantiate scrapers for different aviation job sites
"""

from .absjets_scraper import AbsjetsScraper
from .aegean_scraper import AegeanScraper
from .airfrance_scraper import AirFranceScraper
from .airmalta_scraper import AirMaltaScraper
from .airserbia_scraper import AirSerbiaScraper
from .aena_scraper import AenaScraper
from .airfrancehop_scraper import AirFranceHopScraper
from .aireuropaexpress_scraper import AirEuropaExpressScraper
from .alsieexpress_scraper import AlsieExpressScraper
from .amapolaflyg_scraper import AmapolaFlygScraper
from .aslairlinesbelgium_scraper import ASLAirlinesBelgiumScraper
from .austrianairlines_scraper import AustrianAirlinesScraper
from .blueislands_scraper import BlueIslandsScraper
from .braathens_scraper import BraathensScraper
from .bristow_scraper import BristowScraper
from .brusselsairlines_scraper import BrusselsAirlinesScraper
from .buraqair_scraper import BuraqAirScraper
from .buzz_scraper import BuzzScraper
from .cabotaviation_scraper import CabotAviationScraper
from .signature_aviation import SignatureAviationScraper
from .flygosh_scraper import FlygoshScraper
from .aviationindeed_scraper import AviationIndeedScraper
from .aap_aviation_scraper import AAPAviationScraper
from .indigo_scraper import IndiGoScraper
from .aviationjobsearch_scraper import AviationJobSearchScraper
from .goose_scraper import GooseRecruitmentScraper
from .linkdin_scraper import LinkedInScraper
from .peopleclick_scraper import CargoluxPeopleClickScraper
from .airindia_scraper import AirIndiaScraper
from .aviationcv_scraper import AviationCVScraper
from .jsfirm_scraper import JSFirmScraper
from .allflyingjobs_scraper import AllFlyingJobsScraper
from .emirates_scraper import EmiratesScraper
from .boeing_scraper import BoeingScraper
from .airbus_scraper import AirbusScraper
from .pilots_global_scraper import PilotsGlobalScraper
from .zenon_scraper import ZenonScraper
from .aaae_scraper import AAAEScraper
from .aisats_scraper import AISATSScraper
from .capitalairlines_scraper import CapitalAirlinesScraper
from .carpatair_scraper import CarpatairScraper
from .dat_scraper import DATScraper
from .edelweiss_scraper import EdelweissScraper
from .egyptair_scraper import EgyptairScraper
from .elal_scraper import ElAlScraper
from .ethiopian_scraper import EthiopianScraper
from .eurowings_scraper import EurowingsScraper
from .finnair_scraper import FinnairScraper
from .flybe_scraper import FlybeScraper
from .hahnair_scraper import HahnAirScraper
from .iberia_scraper import IberiaScraper
from .iberiaexpress_scraper import IberiaExpressScraper
from .icelandair_scraper import IcelandairScraper
from .itaairways_scraper import ITAScraper
from .klm_scraper import KLMScraper
from .lot_scraper import LOTScraper
from .lufthansacityline_scraper import LufthansaCityLineScraper
from .norwegian_scraper import NorwegianScraper
from .olympicair_scraper import OlympicAirScraper
from .ryanair_scraper import RyanairScraper
from .sas_scraper import SASScraper
from .smartwings_scraper import SmartWingsScraper
from .swiss_scraper import SwissScraper
from .tap_scraper import TAPScraper
from .transavia_scraper import TransaviaScraper
from .tuiairways_scraper import TuiAirwaysScraper
from .vueling_scraper import VuelingScraper
from .aerlingus_scraper import AerLingusScraper
from .airbaltic_scraper import AirBalticScraper
from .airdolomiti_scraper import AirDolomitiScraper
from .airnostrum_scraper import AirNostrumScraper
from .jmc_scraper import JMCScraper
from .iata_scraper import IataScraper
from .avianation_scraper import AvianationScraper
from .wizzair_scraper import WizzAirScraper
from .cpr_scraper import CPRScraper
from .nbaa_scraper import NBAAScraper
from .starair_scraper import StarAirScraper
from .lufthansa_scraper import LufthansaScraper
from .southwest_scraper import SouthwestScraper
from .ba_scraper import BritishAirwaysScraper
from .cathay_scraper import CathayPacificScraper
from .germanairways_scraper import GermanAirwaysScraper
from .aa_scraper import AmericanAirlinesScraper
from .etihad_scraper import EtihadScraper
from .flydubai_scraper import FlydubaiScraper
from .airarabia_scraper import AirArabiaScraper
from .airarabia_auh_scraper import AirArabiaAuhScraper
from .royaljet_scraper import RoyalJetScraper
from .dubairaw_scraper import DubaiRawScraper
from .easternairways_scraper import EasternAirwaysScraper
from .easyjet_scraper import EasyJetScraper
from .abudhabiaviation_scraper import AbuDhabiAviationScraper
from .falconaviation_scraper import FalconAviationScraper


# Available scrapers
SCRAPERS = {
    'absjets': AbsjetsScraper,
    'aegean': AegeanScraper,
    'airfrance': AirFranceScraper,
    'airfrancehop': AirFranceHopScraper,
    'aena': AenaScraper,
    'aireuropaexpress': AirEuropaExpressScraper,
    'airmalta': AirMaltaScraper,
    'airserbia': AirSerbiaScraper,
    'alsieexpress': AlsieExpressScraper,
    'amapolaflyg': AmapolaFlygScraper,
    'aslairlinesbelgium': ASLAirlinesBelgiumScraper,
    'austrianairlines': AustrianAirlinesScraper,
    'blueislands': BlueIslandsScraper,
    'braathens': BraathensScraper,
    'bristow': BristowScraper,
    'brusselsairlines': BrusselsAirlinesScraper,
    'buraqair': BuraqAirScraper,
    'buzz': BuzzScraper,
    'cabotaviation': CabotAviationScraper,
    'signature': SignatureAviationScraper,
    'flygosh': FlygoshScraper,
    'aviationindeed': AviationIndeedScraper,
    'aap': AAPAviationScraper,
    'indigo': IndiGoScraper,
    'aviationjobsearch': AviationJobSearchScraper,
    'goose': GooseRecruitmentScraper,
    'linkedin': LinkedInScraper,
    'cargolux': CargoluxPeopleClickScraper,
    'airindia': AirIndiaScraper,
    'jsfirm': JSFirmScraper,
    'allflyingjobs': AllFlyingJobsScraper,
    'emirates': EmiratesScraper,
    'boeing': BoeingScraper,
    'airbus': AirbusScraper,
    'pilots_global': PilotsGlobalScraper,
    'aviationcv': AviationCVScraper,
    'zenon': ZenonScraper,
    'aaae': AAAEScraper,
    'aisats': AISATSScraper,
    'jmc': JMCScraper,
    'iata': IataScraper,
    'avianation': AvianationScraper,
    'wizzair': WizzAirScraper,
    'cpr': CPRScraper,
    'nbaa': NBAAScraper,
    'starair': StarAirScraper,
    'lufthansa': LufthansaScraper,
    'southwest': SouthwestScraper,
    'ba': BritishAirwaysScraper,
    'capitalairlines': CapitalAirlinesScraper,
    'carpatair': CarpatairScraper,
    'dat': DATScraper,
    'edelweiss': EdelweissScraper,
    'egyptair': EgyptairScraper,
    'elal': ElAlScraper,
    'ethiopian': EthiopianScraper,
    'eurowings': EurowingsScraper,
    'finnair': FinnairScraper,
    'flybe': FlybeScraper,
    'hahnair': HahnAirScraper,
    'iberia': IberiaScraper,
    'iberiaexpress': IberiaExpressScraper,
    'icelandair': IcelandairScraper,
    'itaairways': ITAScraper,
    'klm': KLMScraper,
    'lot': LOTScraper,
    'lufthansacityline': LufthansaCityLineScraper,
    'norwegian': NorwegianScraper,
    'olympicair': OlympicAirScraper,
    'ryanair': RyanairScraper,
    'sas': SASScraper,
    'smartwings': SmartWingsScraper,
    'swiss': SwissScraper,
    'tap': TAPScraper,
    'transavia': TransaviaScraper,
    'tuiairways': TuiAirwaysScraper,
    'vueling': VuelingScraper,
    'aerlingus': AerLingusScraper,
    'airbaltic': AirBalticScraper,
    'airdolomiti': AirDolomitiScraper,
    'airnostrum': AirNostrumScraper,
    'easternairways': EasternAirwaysScraper,
    'easyjet': EasyJetScraper,
    'cathay': CathayPacificScraper,
    'germanairways': GermanAirwaysScraper,
    'aa': AmericanAirlinesScraper,
    'etihad': EtihadScraper,
    'flydubai': FlydubaiScraper,
    'airarabia': AirArabiaScraper,
    'airarabia_auh': AirArabiaAuhScraper,
    'royaljet': RoyalJetScraper,
    'dubairaw': DubaiRawScraper,
    'abudhabiaviation': AbuDhabiAviationScraper,
    'falconaviation': FalconAviationScraper,
}


def get_scraper(scraper_name: str, config: dict, db_manager=None):
    """
    Factory function to get scraper instance
    
    Args:
        site_name: Name of the site ('signature', 'flygosh', etc.)
        scraper_name: Name of the scraper ('signature', 'flygosh', etc.)
        config: Configuration dictionary for the scraper
        db_manager: Optional database manager for URL tracking
    
    Returns:
        Scraper instance
    """
    if scraper_name not in SCRAPERS:
        raise ValueError(f"Unknown scraper: {scraper_name}. Available: {list(SCRAPERS.keys())}")
    
    scraper_class = SCRAPERS[scraper_name]
    return scraper_class(config, db_manager=db_manager)


def list_scrapers():
    """List all available scrapers"""
    return list(SCRAPERS.keys())
