import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import discord
import pandas as pd
from discord.ext import commands
from jobspy import scrape_jobs

log = logging.getLogger(__name__)

# create data structs here
@dataclass
class SalaryRanges:
    entry_level: int = 0
    mid_level: int = 0
    senior_level: int = 0

@dataclass
class JobMarketAnalysis:
    total_jobs: int
    average_salary: float
    top_hiring_companies: Dict[str, int]
    job_types: Dict[str, int]
    salary_ranges: SalaryRanges

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    job_type: Optional[str]
    min_amount: Optional[float]
    max_amount: Optional[float]
    job_url: str
    site: str


class JobMarketAnalyzer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def scrape_tech_jobs(self, search_term: str = "software engineer", location: str = "United States", results_wanted: int = 50) -> List[JobListing]:
        """Using the Jobspy Library to return a list of JobListing objects"""
        try:
            jobs_df = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor"],
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=168  # last 7 days
            )
            
            # Convert DataFrame to List[JobListing] 
            job_listings: List[JobListing] = []
            for _, row in jobs_df.iterrows():
                job_listing = JobListing(
                    title=str(row.get('title', '')),
                    company=str(row.get('company', '')),
                    location=str(row.get('location', '')),
                    job_type=str(row.get('job_type')) if pd.notna(row.get('job_type')) else None,
                    min_amount=float(row['min_amount']) if pd.notna(row.get('min_amount')) else None,
                    max_amount=float(row['max_amount']) if pd.notna(row.get('max_amount')) else None,
                    job_url=str(row.get('job_url', '')),
                    site=str(row.get('site', ''))
                )
                job_listings.append(job_listing)
            
            return job_listings
            
        except Exception as e:
            log.debug(f"Error scraping jobs: {e}")
            return []

    def analyze_job_market(self, job_listings: List[JobListing]) -> JobMarketAnalysis:
        """Returns useful insights from the list of JobListing objects"""
        if not job_listings:
            return JobMarketAnalysis(
                total_jobs=0,
                average_salary=0.0,
                top_hiring_companies={},
                job_types={},
                salary_ranges=SalaryRanges()
            )

        # Calculate average salary from jobs with salary data
        salary_data = [job for job in job_listings if job.min_amount is not None]
        avg_salary = sum(job.min_amount for job in salary_data) / len(salary_data) if salary_data else 0.0

        # Top hiring companies
        company_counts = {}
        for job in job_listings:
            company_counts[job.company] = company_counts.get(job.company, 0) + 1
        top_companies = dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5])

        # Job types distribution
        job_type_counts = {}
        for job in job_listings:
            job_type = job.job_type or "Not specified"
            job_type_counts[job_type] = job_type_counts.get(job_type, 0) + 1
        top_job_types = dict(sorted(job_type_counts.items(), key=lambda x: x[1], reverse=True)[:3])

        # Salary ranges
        salary_ranges = SalaryRanges()
        if salary_data:
            for job in salary_data:
                if job.min_amount < 70000:
                    salary_ranges.entry_level += 1
                elif 70000 <= job.min_amount < 120000:
                    salary_ranges.mid_level += 1
                else:
                    salary_ranges.senior_level += 1

        return JobMarketAnalysis(
            total_jobs=len(job_listings),
            average_salary=round(avg_salary, 2),
            top_hiring_companies=top_companies,
            job_types=top_job_types,
            salary_ranges=salary_ranges
        )

    @commands.hybrid_command(name='jobmarket') 
    async def job_market(self, ctx, role: str = "software engineer", location: str = "United States"):
        """Discord command which accepts role and location params. Utilizes the scrape_tech_jobs and analyze_job_market functions"""
        await ctx.send(f"Scraping {role} jobs in {location}... This may take a minute or two!")

        try:
            job_listings = self.scrape_tech_jobs(role, location)            
            if not job_listings:
                await ctx.send("Retrieved zero job entries! Please try again later.")
                return

            analysis = self.analyze_job_market(job_listings)

            # Create Discord embed with structured data
            embed = discord.Embed(
                title=f"📊 Tech Job Market Analysis",
                description=f"**Role:** {role.title()}\n**Location:** {location}\n**Data Source:** Indeed, LinkedIn, Glassdoor",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # Total jobs
            embed.add_field(
                name="📈 Total Jobs Available",
                value=f"{analysis.total_jobs} positions",
                inline=True
            )

            # Average salary
            average_salary = f"${analysis.average_salary:,.0f}" if analysis.average_salary > 0 else "Data not available"
            embed.add_field(
                name="💰 Average Salary",
                value=average_salary,
                inline=True
            )

            # Top companies
            if analysis.top_hiring_companies:
                companies_text = "\n".join([f"• {company}: {count}" for company, count in analysis.top_hiring_companies.items()])
                embed.add_field(
                    name="🏢 Top Hiring Companies",
                    value=companies_text,
                    inline=False
                )

            # Salary ranges
            total_salary_jobs = analysis.salary_ranges.entry_level + analysis.salary_ranges.mid_level + analysis.salary_ranges.senior_level
            if total_salary_jobs > 0:
                ranges_text = f"Entry Level: {analysis.salary_ranges.entry_level}\n"
                ranges_text += f"Mid Level: {analysis.salary_ranges.mid_level}\n"
                ranges_text += f"Senior Level: {analysis.salary_ranges.senior_level}"
                embed.add_field(
                    name="📊 Salary Distribution",
                    value=ranges_text,
                    inline=True
                )

            # Job types
            if analysis.job_types:
                types_text = "\n".join([f"• {job_type}: {count}" for job_type, count in analysis.job_types.items()])
                embed.add_field(
                    name="💼 Job Types",
                    value=types_text,
                    inline=True
                )

            embed.set_footer(text="Data is coming from the last 7 days!")

            await ctx.send(embed=embed)

        except Exception as e:
            log.exception(e)
            await ctx.send(f"Error analyzing job market: {str(e)}")

async def setup(bot):
    await bot.add_cog(JobMarketAnalyzer(bot))

    