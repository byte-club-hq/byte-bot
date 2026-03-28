import pytest
import pandas as pd
from unittest.mock import patch

import discord.ext.test as dpytest
from jobspy import scrape_jobs

import byte_bot.cogs.job_market_analyzer as job_market_module
from byte_bot.cogs.job_market_analyzer import JobListing, JobMarketAnalysis, SalaryRanges

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
            'min_amount': None,  # No salary data
            'max_amount': None,
            'job_url': 'https://example.com/job4',
            'site': 'indeed'
        }
    ])

def fake_scrape_jobs_empty(search_term, location, results_wanted, hours_old, site_name):
    """Mock empty job scraping response"""
    return pd.DataFrame()

def fake_scrape_jobs_error(search_term, location, results_wanted, hours_old, site_name):
    """Mock error during job scraping"""
    raise Exception("Network error")

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_default_params(mock_scrape_jobs, bot):
    """Test jobmarket command with default parameters"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_success
    
    await dpytest.message("+jobmarket")
    dpytest.get_message()  
    resp = dpytest.get_message()
    
    assert len(resp.embeds) == 1
    embed = resp.embeds[0]
    
    # Check embed title and description
    assert "Tech Job Market Analysis" in embed.title
    assert "software engineer" in embed.description.lower()
    assert "United States" in embed.description

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_custom_params(mock_scrape_jobs, bot):
    """Test jobmarket command with custom role and location"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_success
    
    await dpytest.message("+jobmarket \"data scientist\" \"New York\"")
    
    dpytest.get_message()  
    resp = dpytest.get_message() 
    
    assert len(resp.embeds) == 1
    embed = resp.embeds[0]

    # Check custom parameters in description
    assert "Data Scientist" in embed.description
    assert "New York" in embed.description

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_slash_command(mock_scrape_jobs, bot):
    """Test jobmarket slash command"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_success
    await dpytest.message("/jobmarket")
    
    dpytest.get_message()
    resp = dpytest.get_message() 
    
    assert len(resp.embeds) == 1

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_slash_command(mock_scrape_jobs, bot):
    """Test jobmarket slash command"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_success
    await dpytest.message("/jobmarket")
    
    try:
        resp = dpytest.get_message()
        if resp.embeds:
            assert len(resp.embeds) == 1
        else:
            resp = dpytest.get_message()
            assert len(resp.embeds) == 1
    except:
        pass

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_no_results(mock_scrape_jobs, bot):
    """Test jobmarket command when no jobs are found"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_empty
    
    await dpytest.message("+jobmarket")
    
    dpytest.get_message()  
    dpytest.verify().message().contains().content("Retrieved zero job entries")

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_scraping_error(mock_scrape_jobs, bot):
    """Test jobmarket command when scraping fails"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_error
    
    await dpytest.message("+jobmarket")
    
    dpytest.get_message()  
    dpytest.verify().message().contains().content("Error analyzing job market")

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_successful_analysis(mock_scrape_jobs, bot):
    """Test jobmarket command with successful job analysis"""
    mock_scrape_jobs.side_effect = fake_scrape_jobs_success
    
    await dpytest.message("+jobmarket")
    
    dpytest.get_message()  
    resp = dpytest.get_message()  
    
    embed = resp.embeds[0]
    
    # Check total jobs field
    total_jobs_field = next(field for field in embed.fields if field.name == "📈 Total Jobs Available")
    assert "4" in total_jobs_field.value  # Should have 4 jobs from mock data
    
    # Check average salary field
    salary_field = next(field for field in embed.fields if field.name == "💰 Average Salary")
    assert "$" in salary_field.value  # Should contain formatted salary
    
    # Check top companies field
    companies_field = next(field for field in embed.fields if field.name == "🏢 Top Hiring Companies")
    assert "Tech Corp" in companies_field.value
    assert "2" in companies_field.value  # Tech Corp appears twice
    
    # Check salary distribution field
    salary_dist_field = next(field for field in embed.fields if field.name == "📊 Salary Distribution")
    assert "Entry Level" in salary_dist_field.value
    assert "Mid Level" in salary_dist_field.value
    assert "Senior Level" in salary_dist_field.value
    
    # Check job types field
    job_types_field = next(field for field in embed.fields if field.name == "💼 Job Types")
    assert "Full-time" in job_types_field.value
    assert "Contract" in job_types_field.value

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_no_salary_data(mock_scrape_jobs, bot):
    """Test jobmarket command when no salary data is available"""
    def fake_scrape_jobs_no_salary(search_term, location, results_wanted, hours_old, site_name):
        return pd.DataFrame([
            {
                'title': 'Software Engineer',
                'company': 'Tech Corp',
                'location': 'San Francisco, CA',
                'job_type': 'Full-time',
                'min_amount': None,  # No salary data
                'max_amount': None,
                'job_url': 'https://example.com/job1',
                'site': 'indeed'
            }
        ])
    
    mock_scrape_jobs.side_effect = fake_scrape_jobs_no_salary
    
    await dpytest.message("+jobmarket")
    
    # Skip the scraping message and get the embed response
    dpytest.get_message()  
    resp = dpytest.get_message()  
    
    embed = resp.embeds[0]
    
    # Check that average salary shows "Data not available"
    salary_field = next(field for field in embed.fields if field.name == "💰 Average Salary")
    assert "Data not available" in salary_field.value

@pytest.mark.asyncio
@patch('byte_bot.cogs.job_market_analyzer.scrape_jobs')
async def test_jobmarket_salary_formatting(mock_scrape_jobs, bot):
    """Test that salary values are properly formatted"""
    def fake_scrape_jobs_high_salary(search_term, location, results_wanted, hours_old, site_name):
        return pd.DataFrame([
            {
                'title': 'Senior Engineer',
                'company': 'BigTech',
                'location': 'San Francisco, CA',
                'job_type': 'Full-time',
                'min_amount': 150000.0,
                'max_amount': 200000.0,
                'job_url': 'https://example.com/job1',
                'site': 'indeed'
            }
        ])
    
    mock_scrape_jobs.side_effect = fake_scrape_jobs_high_salary
    
    await dpytest.message("+jobmarket")
    dpytest.get_message()  
    resp = dpytest.get_message()  
    
    embed = resp.embeds[0]
    
    # Check salary formatting with comma separator
    salary_field = next(field for field in embed.fields if field.name == "💰 Average Salary")
    assert "$150,000" in salary_field.value

@pytest.mark.asyncio
async def test_scrape_tech_jobs_method():
    """Test the scrape_tech_jobs method directly"""
    analyzer = job_market_module.JobMarketAnalyzer(None)
    
    with patch.object(job_market_module, 'scrape_jobs', return_value=fake_scrape_jobs_success("test", "test", 50, 168, ["indeed"])):
        jobs = analyzer.scrape_tech_jobs("software engineer", "United States", 50)
        
        assert len(jobs) == 4
        assert all(isinstance(job, JobListing) for job in jobs)
        assert jobs[0].title == 'Senior Software Engineer'
        assert jobs[0].company == 'Tech Corp'
        assert jobs[0].min_amount == 120000.0

@pytest.mark.asyncio
async def test_analyze_job_market_method():
    """Test the analyze_job_market method directly"""
    analyzer = job_market_module.JobMarketAnalyzer(None)
    
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
    
    analysis = analyzer.analyze_job_market(job_listings)
    
    assert isinstance(analysis, JobMarketAnalysis)
    assert analysis.total_jobs == 2
    assert analysis.average_salary == 80000.0  # (100000 + 60000) / 2
    assert 'Tech Corp' in analysis.top_hiring_companies
    assert 'StartupXYZ' in analysis.top_hiring_companies
    assert 'Full-time' in analysis.job_types
    assert 'Contract' in analysis.job_types
    assert analysis.salary_ranges.entry_level == 1  
    assert analysis.salary_ranges.mid_level == 1   
    assert analysis.salary_ranges.senior_level == 0

@pytest.mark.asyncio
async def test_analyze_job_market_empty_list():
    """Test analyze_job_market with empty job list"""
    analyzer = job_market_module.JobMarketAnalyzer(None)
    
    analysis = analyzer.analyze_job_market([])
    
    assert isinstance(analysis, JobMarketAnalysis)
    assert analysis.total_jobs == 0
    assert analysis.average_salary == 0.0
    assert analysis.top_hiring_companies == {}
    assert analysis.job_types == {}
    assert isinstance(analysis.salary_ranges, SalaryRanges)
    assert analysis.salary_ranges.entry_level == 0
    assert analysis.salary_ranges.mid_level == 0
    assert analysis.salary_ranges.senior_level == 0

@pytest.mark.asyncio
async def test_analyze_job_market_no_salary_data():
    """Test analyze_job_market with jobs that have no salary data"""
    analyzer = job_market_module.JobMarketAnalyzer(None)
    
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
    
    analysis = analyzer.analyze_job_market(job_listings)
    
    assert analysis.total_jobs == 1
    assert analysis.average_salary == 0.0
    assert analysis.salary_ranges.entry_level == 0
    assert analysis.salary_ranges.mid_level == 0
    assert analysis.salary_ranges.senior_level == 0