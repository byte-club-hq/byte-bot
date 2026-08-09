import pandas as pd
from unittest.mock import patch


def fake_scrape_jobs_success(search_term, location, results_wanted, hours_old, site_name):
    """Mock successful job scraping response"""
    return pd.DataFrame([
        {
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'location': 'San Francisco, CA',
            'job_type': 'Full-time',
            'min_amount': 120000.0,
            'max_amount': 180000.0,
            'job_url': 'https://example.com/job1',
            'site': 'indeed'
        },
        {
            'title': 'Software Engineer',
            'company': 'StartupXYZ',
            'location': 'Remote',
            'job_type': 'Full-time',
            'min_amount': 80000.0,
            'max_amount': 120000.0,
            'job_url': 'https://example.com/job2',
            'site': 'linkedin'
        },
        {
            'title': 'Junior Developer',
            'company': 'Tech Corp',
            'location': 'New York, NY',
            'job_type': 'Contract',
            'min_amount': 60000.0,
            'max_amount': 80000.0,
            'job_url': 'https://example.com/job3',
            'site': 'glassdoor'
        },
        {
            'title': 'Data Engineer',
            'company': 'DataInc',
            'location': 'Boston, MA',
            'job_type': 'Full-time',
            'min_amount': None,
            'max_amount': None,
            'job_url': 'https://example.com/job4',
            'site': 'indeed'
        }
    ])


def test_scrape_tech_jobs():
    """Test the scrape_tech_jobs function directly"""
    from byte_bot.cogs.job_market_analyzer import (
        JobListing,
        scrape_tech_jobs,
    )

    with patch('byte_bot.cogs.job_market_analyzer.scrape_jobs', return_value=fake_scrape_jobs_success("test", "test", 50, 168, ["indeed"])):
        jobs = scrape_tech_jobs("software engineer", "United States", 50)
        
        assert len(jobs) == 4
        assert all(isinstance(job, JobListing) for job in jobs)
        assert jobs[0].title == 'Senior Software Engineer'
        assert jobs[0].company == 'Tech Corp'
        assert jobs[0].min_amount == 120000.0


def test_analyze_job_market():
    """Test the analyze_job_market function directly"""
    from byte_bot.cogs.job_market_analyzer import (
        JobListing,
        JobMarketAnalysis,
        SalaryRanges,
        analyze_job_market,
    )

    job_listings = [
        JobListing(
            title='Software Engineer',
            company='Tech Corp',
            location='San Francisco',
            job_type='Full-time',
            min_amount=100000.0,
            max_amount=150000.0,
            job_url='https://example.com',
            site='indeed'
        ),
        JobListing(
            title='Junior Developer',
            company='StartupXYZ',
            location='Remote',
            job_type='Contract',
            min_amount=60000.0,
            max_amount=80000.0,
            job_url='https://example.com',
            site='linkedin'
        )
    ]
    
    analysis = analyze_job_market(job_listings)
    
    assert isinstance(analysis, JobMarketAnalysis)
    assert analysis.total_jobs == 2
    assert analysis.average_salary == 80000.0
    assert 'Tech Corp' in analysis.top_hiring_companies
    assert 'StartupXYZ' in analysis.top_hiring_companies
    assert 'Full-time' in analysis.job_types
    assert 'Contract' in analysis.job_types
    assert analysis.salary_ranges.entry_level == 1  
    assert analysis.salary_ranges.mid_level == 1   
    assert analysis.salary_ranges.senior_level == 0


def test_analyze_job_market_empty_list():
    """Test analyze_job_market with empty job list"""
    from byte_bot.cogs.job_market_analyzer import (
        JobMarketAnalysis,
        SalaryRanges,
        analyze_job_market,
    )

    analysis = analyze_job_market([])
    
    assert isinstance(analysis, JobMarketAnalysis)
    assert analysis.total_jobs == 0
    assert analysis.average_salary == 0.0
    assert analysis.top_hiring_companies == {}
    assert analysis.job_types == {}
    assert isinstance(analysis.salary_ranges, SalaryRanges)
    assert analysis.salary_ranges.entry_level == 0
    assert analysis.salary_ranges.mid_level == 0
    assert analysis.salary_ranges.senior_level == 0


def test_analyze_job_market_no_salary_data():
    """Test analyze_job_market with jobs that have no salary data"""
    from byte_bot.cogs.job_market_analyzer import (
        JobListing,
        analyze_job_market,
    )

    job_listings = [
        JobListing(
            title='Software Engineer',
            company='Tech Corp',
            location='San Francisco',
            job_type='Full-time',
            min_amount=None,  
            max_amount=None,
            job_url='https://example.com',
            site='indeed'
        )
    ]
    
    analysis = analyze_job_market(job_listings)
    
    assert analysis.total_jobs == 1
    assert analysis.average_salary == 0.0
    assert analysis.salary_ranges.entry_level == 0
    assert analysis.salary_ranges.mid_level == 0
    assert analysis.salary_ranges.senior_level == 0
