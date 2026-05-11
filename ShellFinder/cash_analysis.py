import pandas as pd
import requests
import os
from datetime import datetime
import re
import logging
import csv
import io

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cash_extraction.log'),
        logging.StreamHandler()
    ]
)

def download_asx_directory():
    """Download ASX company directory"""
    url = "https://asx.api.markitdigital.com/asx-research/1.0/companies/directory/file"
    params = {
        'access_token': '83ff96335c2d45a094df02a206a39ff4'
    }
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Create a mapping file
            df = pd.read_csv(io.StringIO(response.text))
            
            # Clean and select relevant columns
            mapping_df = df[['ASX code', 'Company name', 'Market Cap']].copy()
            mapping_df.columns = ['Company_Code', 'Company_Name', 'Market_Cap_Millions']
            
            # Convert market cap to millions
            mapping_df['Market_Cap_Millions'] = pd.to_numeric(mapping_df['Market_Cap_Millions'].str.replace(',', ''), errors='coerce') / 1000000
            
            # Save mapping file
            mapping_df.to_csv('company_mapping.csv', index=False)
            return mapping_df
    except Exception as e:
        logging.error(f"Error downloading ASX directory: {str(e)}")
        return None

def extract_cash_balance(text):
    """
    Extract cash balance from text using specific patterns
    Returns tuple of (current_quarter_balance, success)
    """
    # Pattern for 8.4 format
    pattern1 = r"8\.4\s*Cash\s+and\s+cash\s+equivalents\s+at\s+quarter\s+end.*?(\d[\d,]+)"
    
    # Pattern for 5.5 format
    pattern2 = r"5\.5\s*Cash\s+and\s+cash\s+equivalents\s+at\s+end\s+of\s*\n*\s*quarter.*?(\d[\d,]+)"
    
    patterns = [pattern1, pattern2]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                # Convert to millions if in thousands
                if value > 100:  # Assume it's in thousands if > 100
                    value /= 1000
                return value, True
            except ValueError as e:
                logging.warning(f"Error converting value: {e}")
                
    return None, False

def determine_financial_quarter(filename):
    """
    Extract year and quarter information from filename
    Example: AAR-20241021-Quarterly Activities & Cashflow Report-First Quarter Activities Report.txt
    """
    try:
        # Split filename into parts
        parts = filename.split('-')
        if len(parts) < 4:
            return None, None, None
            
        # Extract date from second part (YYYYMMDD)
        date_str = parts[1]
        year = date_str[:4]  # Get YYYY from YYYYMMDD
        
        # Extract quarter from the last part
        quarter_text = parts[-1].lower()
        
        # Map quarter text to quarter number
        if 'first quarter' in quarter_text:
            qtr = 'Q1'
        elif 'second quarter' in quarter_text:
            qtr = 'Q2'
        elif 'third quarter' in quarter_text:
            qtr = 'Q3'
        elif 'fourth quarter' in quarter_text:
            qtr = 'Q4'
        else:
            qtr = None
            
        if qtr and year:
            return qtr, year, f"FY{year[2:]}"
        
        return None, None, None
        
    except Exception as e:
        logging.error(f"Error parsing filename {filename}: {str(e)}")
        return None, None, None

def analyze_cash_balances():
    """Analyze cash balances from text files and calculate enterprise values"""
    base_dir = '/home/coops/scraperproject/ASX_Reports'
    text_dir = os.path.join(base_dir, 'Texts')
    results_dir = os.path.join(base_dir, 'Results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Download/load company mapping first
    mapping_df = download_asx_directory()
    if mapping_df is None:
        logging.error("Failed to get ASX company directory")
        return
    
    company_mapping = dict(zip(mapping_df['Company_Code'], mapping_df['Company_Name']))
    successful_extractions = []
    failed_extractions = []
    
    # Get all text files
    for filename in os.listdir(text_dir):
        try:
            if not filename.endswith('.txt'):
                continue
            
            # Parse filename components
            parts = filename.split('-')
            if len(parts) < 4:
                continue
            
            company_code = parts[0]
            date_str = parts[1]
            
            # Get company name from mapping
            company_name = company_mapping.get(company_code, company_code)
            
            # Extract quarter information from filename
            fin_quarter, year, financial_year = determine_financial_quarter(filename)
            
            if not all([fin_quarter, year, financial_year]):
                logging.warning(f"Could not determine quarter information for {filename}")
                continue
            
            # Read and analyze file
            with open(os.path.join(text_dir, filename), 'r', encoding='utf-8') as f:
                text = f.read()
            
            cash_balance, success = extract_cash_balance(text)
            
            file_info = {
                'Company_Code': company_code,
                'Company_Name': company_name,
                'Report_Date': datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),
                'Calendar_Year': year,
                'Financial_Year': financial_year,
                'Financial_Quarter': fin_quarter,
                'Cash_Balance_Millions': round(cash_balance, 3) if cash_balance else None
            }
            
            if success and cash_balance is not None:
                successful_extractions.append(file_info)
                logging.info(f"Successfully extracted cash balance for {company_code}: {cash_balance}M ({financial_year} {fin_quarter})")
            else:
                failed_extractions.append({**file_info, 'Error': 'Failed to extract cash balance'})
                logging.warning(f"Failed to extract cash balance from {filename}")
                
        except Exception as e:
            logging.error(f"Error processing {filename}: {str(e)}")
            failed_extractions.append({
                'Filename': filename,
                'Error': str(e)
            })
    
    # Save successful extractions
    if successful_extractions:
        df_success = pd.DataFrame(successful_extractions)
        
        # Reorder columns
        column_order = [
            'Company_Code',
            'Company_Name',
            'Report_Date',
            'Calendar_Year',
            'Financial_Year',
            'Financial_Quarter',
            'Cash_Balance_Millions'
        ]
        df_success = df_success[column_order]
        
        # Sort by company code and date
        df_success = df_success.sort_values(['Company_Code', 'Report_Date'])
        
        # Save detailed cash balances
        success_file = os.path.join(results_dir, 'cash_balances.csv')
        df_success.to_csv(success_file, index=False)
        logging.info(f"Saved successful extractions to {success_file}")
        
        # Create quarterly summary
        pivot_summary = pd.pivot_table(
            df_success,
            values='Cash_Balance_Millions',
            index=['Company_Code', 'Company_Name'],
            columns=['Financial_Year', 'Financial_Quarter'],
            aggfunc='first'
        ).round(3)
        
        summary_file = os.path.join(results_dir, 'cash_balances_summary.csv')
        pivot_summary.to_csv(summary_file)
        logging.info(f"Saved summary to {summary_file}")
        
        # Calculate Enterprise Values
        # Get latest cash balance for each company
        latest_cash = df_success.sort_values('Report_Date').groupby('Company_Code').last().reset_index()
        
        # Merge with company mapping to get market caps
        results_df = mapping_df.merge(
            latest_cash[['Company_Code', 'Cash_Balance_Millions', 'Report_Date', 'Financial_Quarter', 'Financial_Year']], 
            on='Company_Code', 
            how='left'
        )
        
        # Calculate enterprise value
        results_df['Enterprise_Value_Millions'] = results_df['Market_Cap_Millions'] - results_df['Cash_Balance_Millions']
        
        # Sort by enterprise value
        results_df = results_df.sort_values('Enterprise_Value_Millions')
        
        # Reorder columns for clarity
        ev_columns = [
            'Company_Code',
            'Company_Name',
            'Market_Cap_Millions',
            'Cash_Balance_Millions',
            'Enterprise_Value_Millions',
            'Financial_Quarter',
            'Financial_Year',
            'Report_Date'
        ]
        results_df = results_df[ev_columns]
        
        # Round numeric columns
        numeric_columns = ['Market_Cap_Millions', 'Cash_Balance_Millions', 'Enterprise_Value_Millions']
        results_df[numeric_columns] = results_df[numeric_columns].round(3)
        
        # Save enterprise values
        ev_file = os.path.join(results_dir, 'enterprise_values.csv')
        results_df.to_csv(ev_file, index=False)
        logging.info(f"Saved enterprise values to {ev_file}")
        
        # Print summary of lowest enterprise values
        print("\nTop 10 Companies by Lowest Enterprise Value:")
        print(results_df.head(10).to_string())
    
    # Save failed extractions
    if failed_extractions:
        df_failed = pd.DataFrame(failed_extractions)
        failed_file = os.path.join(results_dir, 'failed_extractions.csv')
        df_failed.to_csv(failed_file, index=False)
        logging.info(f"Saved failed extractions to {failed_file}")
    
    return successful_extractions, failed_extractions

def test_extraction():
    """Test function to verify cash balance extraction"""
    print("\nRunning test extraction...")
    
    # Test Case 1: 8.4 format
    test_text1 = """8.4 Cash and cash equivalents at quarter end (item 4.6) 11,573"""
    cash_balance1, success1 = extract_cash_balance(test_text1)
    print(f"Test 1 - 8.4 format:")
    print(f"Expected: 11.573M")
    print(f"Got: {cash_balance1}M")
    print("Result: ", "✓ Passed" if cash_balance1 == 11.573 else "✗ Failed")
    
    # Test Case 2: Filename parsing
    test_filename = "AAR-20241021-Quarterly Activities & Cashflow Report-First Quarter Activities Report.txt"
    qtr, year, fy = determine_financial_quarter(test_filename)
    print(f"\nTest 2 - Filename parsing:")
    print(f"Expected: Q1, 2024, FY24")
    print(f"Got: {qtr}, {year}, {fy}")
    print("Result: ", "✓ Passed" if (qtr, year, fy) == ('Q1', '2024', 'FY24') else "✗ Failed")

if __name__ == "__main__":
    try:
        # Run tests first
        test_extraction()
        
        # Run the main analysis
        logging.info("\nStarting cash balance and enterprise value analysis...")
        successful, failed = analyze_cash_balances()
        
        # Print summary
        print(f"\nProcessing complete!")
        print(f"Successfully processed: {len(successful)} files")
        print(f"Failed to process: {len(failed)} files")
        
        if failed:
            print("\nFiles that failed extraction:")
            for fail in failed[:10]:
                print(f"- {fail.get('Filename', 'Unknown file')} : {fail.get('Error', 'Unknown error')}")
            if len(failed) > 10:
                print(f"... and {len(failed) - 10} more")
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")