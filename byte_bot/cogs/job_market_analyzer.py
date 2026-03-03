from discord.ext import commands
import discord
from jobspy import scrape_jobs
import pandas as pd
from datetime import datetime

class job_market_analyzer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def scrape_tech_jobs(self, search_term="software engineer", location="United States", results_wanted=50): # this returns a dataframe 
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor"],
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=168  # last 7 days
            )
            return jobs
        except Exception as e:
            print(f"Error scraping jobs: {e}")
            return pd.DataFrame()

    def analyze_job_market(self, jobs_df): # here we do aggregations on the dataframe
        if jobs_df.empty:
            return {
                'total_jobs': 0,
                'average_salary': 0,
                'top_hiring_companies': {},
                'job_types': {},
                'salary_ranges': {}
            }

        salary_data = jobs_df[jobs_df['min_amount'].notna()]
        avg_salary = salary_data['min_amount'].mean() if not salary_data.empty else 0
        top_companies = jobs_df['company'].value_counts().head(5).to_dict()
        job_types = jobs_df['job_type'].value_counts().head(3).to_dict()

        if not salary_data.empty:
            salary_ranges = {
                'entry_level': len(salary_data[salary_data['min_amount'] < 70000]),
                'mid_level': len(salary_data[(salary_data['min_amount'] >= 70000) & (salary_data['min_amount'] < 120000)]),
                'senior_level': len(salary_data[salary_data['min_amount'] >= 120000])
            }

        else: # fallback to empty values
            salary_ranges = {'entry_level': 0, 'mid_level': 0, 'senior_level': 0}

        return {
            'total_jobs': len(jobs_df),
            'average_salary': round(avg_salary, 2),
            'top_hiring_companies': top_companies,
            'job_types': job_types,
            'salary_ranges': salary_ranges
        }

    @commands.hybrid_command(name='jobmarket') # the command puts everything together
    async def job_market(self, ctx, role: str = "software engineer", location: str = "United States"): # default to swe, USA
        await ctx.send(f"Scraping {role} jobs in {location}... This may take a minute or two!")

        try:
            jobs_df = self.scrape_tech_jobs(role, location)            
            if jobs_df.empty:
                await ctx.send("Retrieved zero job entries! Please try again later.")
                return

            analysis = self.analyze_job_market(jobs_df)

            # creating a cool embed for the discord
            embed = discord.Embed(
                title=f"📊 Tech Job Market Analysis",
                description=f"**Role:** {role.title()}\n**Location:** {location}\n**Data Source:** Indeed, LinkedIn, Glassdoor",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="📈 Total Jobs Available",
                value=f"{analysis['total_jobs']} positions",
                inline=True
            )

            if analysis['average_salary'] > 0:
                embed.add_field(
                    name="💰 Average Salary",
                    value=f"${analysis['average_salary']:,.0f}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="💰 Average Salary",
                    value="Data not available",
                    inline=True
                )

            # top companies
            if analysis['top_hiring_companies']:
                companies_text = "\n".join([f"• {company}: {count}" for company, count in analysis['top_hiring_companies'].items()])
                embed.add_field(
                    name="🏢 Top Hiring Companies",
                    value=companies_text,
                    inline=False
                )

            # salary ranges
            if sum(analysis['salary_ranges'].values()) > 0:
                ranges_text = f"Entry Level: {analysis['salary_ranges']['entry_level']}\n"
                ranges_text += f"Mid Level: {analysis['salary_ranges']['mid_level']}\n"
                ranges_text += f"Senior Level: {analysis['salary_ranges']['senior_level']}"
                embed.add_field(
                    name="📊 Salary Distribution",
                    value=ranges_text,
                    inline=True
                )

            # job types
            if analysis['job_types']:
                types_text = "\n".join([f"• {job_type}: {count}" for job_type, count in analysis['job_types'].items()])
                embed.add_field(
                    name="💼 Job Types",
                    value=types_text,
                    inline=True
                )

            embed.set_footer(text="Data is coming from the last 7 days!")

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Error analyzing job market: {str(e)}")

async def setup(bot):
    await bot.add_cog(job_market_analyzer(bot))

    