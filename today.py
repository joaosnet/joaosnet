"""
GitHub Profile README Updater
Fetches stats from GitHub API and updates SVG files with dynamic data.
Also converts GitHub profile picture to ASCII art automatically.

João Natividade (joaosnet), 2024-2025
Inspired by Andrew6rant/Andrew6rant
"""

import datetime
from dateutil import relativedelta
import requests
import os
from lxml import etree
from io import BytesIO
from PIL import Image

# Configuration
HEADERS = {'authorization': 'token ' + os.environ.get('ACCESS_TOKEN', '')}
USER_NAME = os.environ.get('USER_NAME', 'joaosnet')
BIRTH_YEAR = 2001  # Only year, no date exposed

# Language classification
PROGRAMMING_LANGUAGES = {'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#', 'Go', 'Rust', 'Kotlin', 'Swift', 'Ruby', 'PHP', 'Dart', 'Scala'}
MARKUP_LANGUAGES = {'HTML', 'CSS', 'SCSS', 'Sass', 'Less', 'Markdown', 'JSON', 'YAML', 'XML', 'LaTeX', 'Dockerfile'}

# ASCII art configuration
ASCII_CHARS = " .:-=+*#%@"  # From lightest to darkest
ASCII_WIDTH = 35  # Characters wide
ASCII_HEIGHT = 24  # Lines tall


def get_profile_picture_url():
    """Get the user's GitHub profile picture URL."""
    query = '''
    query($login: String!) {
        user(login: $login) {
            avatarUrl
        }
    }'''
    result = simple_request(query, {'login': USER_NAME})
    return result['data']['user']['avatarUrl']


def image_to_ascii(image_url: str) -> list[str]:
    """Convert an image URL to ASCII art."""
    # Download image
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Resize image to ASCII dimensions (adjust aspect ratio for terminal chars)
    img = img.resize((ASCII_WIDTH, ASCII_HEIGHT))
    
    # Convert pixels to ASCII characters
    ascii_lines = []
    pixels = list(img.getdata())
    
    for y in range(ASCII_HEIGHT):
        line = ""
        for x in range(ASCII_WIDTH):
            pixel = pixels[y * ASCII_WIDTH + x]
            # Map pixel value (0-255) to ASCII character
            char_index = int(pixel / 256 * len(ASCII_CHARS))
            char_index = min(char_index, len(ASCII_CHARS) - 1)
            line += ASCII_CHARS[char_index]
        ascii_lines.append(line)
    
    return ascii_lines


def calculate_age():
    """Calculate age from birth year (no date exposed)."""
    current_year = datetime.datetime.now().year
    age = current_year - BIRTH_YEAR
    return f"{age} years"


def simple_request(query, variables):
    """Make a GraphQL request to GitHub API."""
    request = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': variables},
        headers=HEADERS
    )
    if request.status_code == 200:
        return request.json()
    raise Exception(f'GraphQL request failed: {request.status_code} - {request.text}')


def get_user_stats():
    """Fetch user stats: repos, stars, followers."""
    query = '''
    query($login: String!) {
        user(login: $login) {
            repositories(first: 100, ownerAffiliations: [OWNER]) {
                totalCount
                nodes {
                    stargazerCount
                    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                        nodes {
                            name
                        }
                    }
                }
            }
            contributionsCollection {
                totalCommitContributions
                restrictedContributionsCount
            }
            repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
                totalCount
            }
            followers {
                totalCount
            }
        }
    }'''
    
    result = simple_request(query, {'login': USER_NAME})
    user = result['data']['user']
    
    repos = user['repositories']['totalCount']
    stars = sum(repo['stargazerCount'] for repo in user['repositories']['nodes'])
    followers = user['followers']['totalCount']
    commits = user['contributionsCollection']['totalCommitContributions']
    commits += user['contributionsCollection']['restrictedContributionsCount']
    contrib = user['repositoriesContributedTo']['totalCount']
    
    # Collect languages
    all_languages = set()
    for repo in user['repositories']['nodes']:
        for lang in repo['languages']['nodes']:
            all_languages.add(lang['name'])
    
    return {
        'repos': repos,
        'stars': stars,
        'followers': followers,
        'commits': commits,
        'contrib': contrib,
        'languages': all_languages
    }


def get_loc_stats():
    """Get lines of code stats (simplified version)."""
    query = '''
    query($login: String!) {
        user(login: $login) {
            repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR]) {
                nodes {
                    nameWithOwner
                    defaultBranchRef {
                        target {
                            ... on Commit {
                                history(first: 1) {
                                    totalCount
                                }
                            }
                        }
                    }
                }
            }
        }
    }'''
    
    result = simple_request(query, {'login': USER_NAME})
    repos = result['data']['user']['repositories']['nodes']
    
    total_commits = 0
    for repo in repos:
        if repo['defaultBranchRef'] and repo['defaultBranchRef']['target']:
            total_commits += repo['defaultBranchRef']['target']['history']['totalCount']
    
    # Estimate LoC based on commits (rough approximation)
    estimated_loc = total_commits * 50
    estimated_add = int(estimated_loc * 1.2)
    estimated_del = int(estimated_loc * 0.2)
    
    return {
        'loc': estimated_loc,
        'add': estimated_add,
        'del': estimated_del
    }


def format_languages(all_languages):
    """Separate languages into programming and markup categories."""
    prog = [lang for lang in all_languages if lang in PROGRAMMING_LANGUAGES]
    markup = [lang for lang in all_languages if lang in MARKUP_LANGUAGES]
    
    prog_order = ['Python', 'JavaScript', 'TypeScript', 'C++', 'C', 'Java', 'Go', 'Rust']
    markup_order = ['HTML', 'CSS', 'SCSS', 'Markdown', 'JSON', 'YAML', 'Dockerfile']
    
    prog = sorted(prog, key=lambda x: prog_order.index(x) if x in prog_order else 999)
    markup = sorted(markup, key=lambda x: markup_order.index(x) if x in markup_order else 999)
    
    return {
        'programming': ', '.join(prog[:5]) if prog else 'Python',
        'markup': ', '.join(markup[:5]) if markup else 'HTML, CSS'
    }


def update_svg(filename, stats, loc_stats, languages, ascii_art):
    """Update SVG file with new stats and ASCII art."""
    tree = etree.parse(filename)
    root = tree.getroot()
    
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Update text elements
    updates = {
        'age_data': calculate_age(),
        'languages_prog': languages['programming'],
        'languages_markup': languages['markup'],
        'repo_data': str(stats['repos']),
        'star_data': str(stats['stars']),
        'follower_data': str(stats['followers']),
        'commit_data': f"{stats['commits']:,}",
        'contrib_data': str(stats['contrib']),
        'loc_data': f"{loc_stats['loc']:,}",
        'loc_add': f"{loc_stats['add']:,}",
        'loc_del': f"{loc_stats['del']:,}",
        'last_updated': datetime.datetime.now().strftime('%Y-%m-%d')
    }
    
    for element_id, value in updates.items():
        for elem in root.iter():
            if elem.get('id') == element_id:
                elem.text = value
                break
    
    # Update ASCII art in the SVG
    # Find the ASCII art text element and update its tspan children
    for elem in root.iter():
        if elem.get('class') == 'ascii' or 'ascii' in (elem.get('class') or ''):
            # Clear existing tspans and add new ones
            tspans = list(elem)
            for i, line in enumerate(ascii_art):
                if i < len(tspans):
                    tspans[i].text = line
    
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"Updated {filename}")


def main():
    """Main function to update README stats."""
    print("Fetching GitHub stats...")
    
    try:
        # Get profile picture and convert to ASCII
        print("  Generating ASCII art from profile picture...")
        avatar_url = get_profile_picture_url()
        ascii_art = image_to_ascii(avatar_url)
        print(f"  ASCII art generated ({len(ascii_art)} lines)")
        
        # Get stats
        stats = get_user_stats()
        print(f"  Repos: {stats['repos']}, Stars: {stats['stars']}, Followers: {stats['followers']}")
        print(f"  Commits: {stats['commits']}, Contributed to: {stats['contrib']}")
        print(f"  Languages found: {stats['languages']}")
        
        # Get LoC stats
        loc_stats = get_loc_stats()
        print(f"  Estimated LoC: {loc_stats['loc']:,}")
        
        # Format languages
        languages = format_languages(stats['languages'])
        print(f"  Programming: {languages['programming']}")
        print(f"  Markup: {languages['markup']}")
        
        # Update SVGs
        update_svg('dark_mode.svg', stats, loc_stats, languages, ascii_art)
        update_svg('light_mode.svg', stats, loc_stats, languages, ascii_art)
        
        print("\nDone! SVG files updated successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == '__main__':
    main()
