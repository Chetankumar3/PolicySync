"""Seed LanceDB with sample RBI regulatory data for testing"""
import sys
sys.path.insert(0, '.')
from ingestion import initialize_db, ingest_document

SAMPLE_DOCS = [
    {
        "source": "RBI Capital Adequacy Guidelines",
        "url": "https://www.rbi.org.in",
        "date": "2024-01-15",
        "text": """Capital Adequacy Requirements for Scheduled Commercial Banks:
        The minimum Capital to Risk-weighted Assets Ratio (CRAR) for scheduled commercial 
        banks in India is 10.5%, which includes a Capital Conservation Buffer (CCB) of 2.5%.
        Tier I capital must be at least 8.5% of risk-weighted assets, of which Common Equity 
        Tier 1 (CET1) capital must be at least 5.5%. Tier II capital can be at most 2% of 
        risk-weighted assets. Banks failing to maintain minimum CRAR are subject to Prompt 
        Corrective Action (PCA) framework by RBI."""
    },
    {
        "source": "RBI KYC Master Directions 2016",
        "url": "https://www.rbi.org.in",
        "date": "2024-02-10",
        "text": """Know Your Customer (KYC) Requirements:
        All banks must follow KYC norms for customer identification and verification.
        KYC involves: (1) Customer Identification Procedure - collecting name, address, 
        identity proof; (2) Customer Due Diligence (CDD) - understanding the nature of 
        customer's business and source of funds; (3) Enhanced Due Diligence for high-risk 
        customers including PEPs (Politically Exposed Persons); (4) Ongoing monitoring of 
        transactions. Officially Valid Documents (OVDs) include Aadhaar, Passport, Voter ID, 
        Driving License, NREGA job card, and PAN card."""
    },
    {
        "source": "RBI Priority Sector Lending Guidelines",
        "url": "https://www.rbi.org.in",
        "date": "2024-03-01",
        "text": """Priority Sector Lending (PSL) Guidelines:
        Domestic scheduled commercial banks and foreign banks with 20+ branches must lend 
        40% of Adjusted Net Bank Credit (ANBC) to priority sectors. Sub-targets include:
        Agriculture: 18% of ANBC (of which 10% to small and marginal farmers);
        Micro Enterprises: 7.5% of ANBC;
        Weaker Sections: 12% of ANBC.
        Priority sectors include Agriculture, MSMEs, Export Credit, Education, Housing, 
        Social Infrastructure, and Renewable Energy. Shortfall in PSL targets requires 
        contribution to RIDF (Rural Infrastructure Development Fund)."""
    },
    {
        "source": "RBI Monetary Policy Report 2024",
        "url": "https://www.rbi.org.in",
        "date": "2024-04-05",
        "text": """RBI Monetary Policy and Key Rates:
        The Repo Rate is the rate at which RBI lends short-term money to commercial banks 
        against government securities. As of 2024, the repo rate is 6.50%. 
        The Standing Deposit Facility (SDF) rate is 6.25% and the Marginal Standing Facility 
        (MSF) rate is 6.75%. The Cash Reserve Ratio (CRR) is 4.50% of Net Demand and Time 
        Liabilities (NDTL). The Statutory Liquidity Ratio (SLR) is 18% of NDTL. 
        These rates are reviewed by the Monetary Policy Committee (MPC) every two months."""
    },
    {
        "source": "RBI FDI Policy Guidelines",
        "url": "https://www.rbi.org.in",
        "date": "2024-01-20",
        "text": """Foreign Direct Investment (FDI) in Banking Sector:
        FDI in private sector banks is permitted up to 74% under the automatic route 
        (beyond 49% requires RBI approval). FDI in public sector banks is capped at 20%.
        For non-banking financial companies (NBFCs), 100% FDI is permitted under automatic 
        route. Foreign Portfolio Investment (FPI) in government securities is subject to 
        limits set by RBI. Foreign banks can operate in India either as branches or as 
        wholly-owned subsidiaries (WOS). WOS route is preferred for systemically important 
        foreign banks."""
    },
    {
        "source": "RBI Digital Banking Guidelines 2023",
        "url": "https://www.rbi.org.in",
        "date": "2023-09-15",
        "text": """Digital Banking and Cyber Security Guidelines:
        RBI has issued guidelines for Digital Banking Units (DBUs) to provide paperless 
        banking services. All banks must implement robust cybersecurity frameworks including:
        multi-factor authentication for transactions above Rs. 5000, real-time fraud 
        monitoring, data localization requirements for payment data. Banks must report 
        cyber incidents to RBI within 2-6 hours of detection. The RBI's framework for 
        Prepaid Payment Instruments (PPIs) allows maximum wallet balance of Rs. 2 lakh 
        for full-KYC customers."""
    }
]

if __name__ == "__main__":
    print("Seeding LanceDB with sample RBI data...")
    db = initialize_db()
    
    for doc in SAMPLE_DOCS:
        result = ingest_document(
            text=doc["text"],
            source_name=doc["source"],
            source_url=doc["url"],
            db=db,
            document_date=doc["date"]
        )
        print(f"✓ Ingested: {doc['source']} — {result['chunks_created']} chunks")
    
    print("\nSeeding complete! Run /status to verify.")