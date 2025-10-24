// Mock游戏数据 - 从CSV自动生成
// 生成时间: 2025-10-19T20:33:01.370Z
// 数据源: backend/exports copy/new_games_2025-10-13.csv

import { GameSnapshot, GameSummary } from "../types";

// Mock游戏概要数据
const mockGameSummaries: GameSummary[] = [
  {
    "id": 1,
    "steam_appid": 3688970,
    "name": "Woolly",
    "steam_url": "https://store.steampowered.com/app/3688970",
    "website": "",
    "developers": "Anneka Tran",
    "publishers": "Anneka Tran",
    "categories": "Single-player;Camera Comfort;Custom Volume Controls;Mouse Only Option;Save Anytime;Family Sharing",
    "genres": "Casual;Indie",
    "tags": "Casual;Indie",
    "latest_release_date": "November 2025",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 2,
    "steam_appid": 3620390,
    "name": "Aberrate Inc.",
    "steam_url": "https://store.steampowered.com/app/3620390",
    "website": "",
    "developers": "Aberrate Team",
    "publishers": "Aberrate Team",
    "categories": "Single-player;Partial Controller Support;Family Sharing",
    "genres": "Casual;Indie",
    "tags": "Casual;Indie",
    "latest_release_date": "To be announced",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 3,
    "steam_appid": 3868690,
    "name": "Cozy Florist",
    "steam_url": "https://store.steampowered.com/app/3868690",
    "website": "",
    "developers": "Two Cats Games",
    "publishers": "Two Cats Games",
    "categories": "Single-player;Steam Achievements;Full controller support;Family Sharing",
    "genres": "Casual;Indie;Simulation;Strategy",
    "tags": "Casual;Indie;Simulation;Strategy",
    "latest_release_date": "2026",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 4,
    "steam_appid": 2572310,
    "name": "Nick's Saturday Morning Games",
    "steam_url": "https://store.steampowered.com/app/2572310",
    "website": "",
    "developers": "Croaking Kero",
    "publishers": "Croaking Kero",
    "categories": "Single-player;Custom Volume Controls;Keyboard Only Option;Playable without Timed Input;Family Sharing",
    "genres": "Casual;Indie;Early Access",
    "tags": "Casual;Indie;Early Access",
    "latest_release_date": "Oct 31, 2025",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 5,
    "steam_appid": 2987560,
    "name": "Rockthesea",
    "steam_url": "https://store.steampowered.com/app/2987560",
    "website": "https://www.demoartstudio.com",
    "developers": "Insexsity_team;Insexsity_team;Insexsity;Insexsity_team",
    "publishers": "Demoartstudio.com;Demoartstudio;Demoartstudio",
    "categories": "Single-player;Custom Volume Controls;Mouse Only Option;Save Anytime;Stereo Sound;Touch Only Option;Family Sharing",
    "genres": "Action;Adventure;Indie;RPG;Early Access",
    "tags": "Action;Adventure;Indie;RPG;Early Access",
    "latest_release_date": "Coming soon",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 6,
    "steam_appid": 3868740,
    "name": "Vet Van Organizer",
    "steam_url": "https://store.steampowered.com/app/3868740",
    "website": "",
    "developers": "Two Cats Games",
    "publishers": "Two Cats Games",
    "categories": "Single-player;Steam Achievements;Full controller support;Family Sharing",
    "genres": "Casual;Indie",
    "tags": "Casual;Indie",
    "latest_release_date": "2026",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 7,
    "steam_appid": 4062240,
    "name": "Wonder Library : Prologue",
    "steam_url": "https://store.steampowered.com/app/4062240",
    "website": "https://www.wonderlibrarygame.com/",
    "developers": "Areumdamda Media Lab",
    "publishers": "Areumdamda Inc.",
    "categories": "Single-player;Family Sharing",
    "genres": "Action;Adventure;Casual;Indie;Simulation",
    "tags": "Action;Adventure;Casual;Indie;Simulation",
    "latest_release_date": "Coming soon",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 8,
    "steam_appid": 3974220,
    "name": "SHELLSTORM: The Great War",
    "steam_url": "https://store.steampowered.com/app/3974220",
    "website": "https://www.hypermadinteractive.com/shellstorm",
    "developers": "Hypermad interactive",
    "publishers": "Hypermad interactive",
    "categories": "Single-player;Multi-player;PvP;Online PvP;Camera Comfort;Custom Volume Controls;Playable without Timed Input;Stereo Sound;Surround Sound;Family Sharing",
    "genres": "Action;Indie;Simulation;Strategy",
    "tags": "Action;Indie;Simulation;Strategy",
    "latest_release_date": "To be announced",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 9,
    "steam_appid": 3871310,
    "name": "Rustmire",
    "steam_url": "https://store.steampowered.com/app/3871310",
    "website": "",
    "developers": "MimicMimijeok",
    "publishers": "MimicMimijeok",
    "categories": "Single-player;Multi-player;PvP;Online PvP;Custom Volume Controls;Mouse Only Option;Save Anytime;Stereo Sound;Family Sharing",
    "genres": "Adventure;Indie;Strategy",
    "tags": "Adventure;Indie;Strategy",
    "latest_release_date": "Q1 2026",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 10,
    "steam_appid": 4072010,
    "name": "Backgammon Premium",
    "steam_url": "https://store.steampowered.com/app/4072010",
    "website": "https://backgammonpremium.com/",
    "developers": "Spectrum.Games International Ltd",
    "publishers": "Spectrum.Games International Ltd",
    "categories": "Multi-player;PvP;Online PvP;Cross-Platform Multiplayer;In-App Purchases",
    "genres": "Casual;Free To Play",
    "tags": "Casual;Free To Play",
    "latest_release_date": "Nov 17, 2025",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 11,
    "steam_appid": 4059210,
    "name": "Face Interrogation",
    "steam_url": "https://store.steampowered.com/app/4059210",
    "website": "",
    "developers": "ODale Studios",
    "publishers": "ODale Studios",
    "categories": "Single-player;Steam Achievements;Family Sharing",
    "genres": "Action;Adventure;Simulation",
    "tags": "Action;Adventure;Simulation",
    "latest_release_date": "2026",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 12,
    "steam_appid": 3653230,
    "name": "Virtual Perspective",
    "steam_url": "https://store.steampowered.com/app/3653230",
    "website": "",
    "developers": "Coreplix Studios",
    "publishers": "Coreplix Studios",
    "categories": "Single-player;Full controller support;Family Sharing",
    "genres": "Action",
    "tags": "Action",
    "latest_release_date": "To be announced",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 13,
    "steam_appid": 4047980,
    "name": "Draw & Play !",
    "steam_url": "https://store.steampowered.com/app/4047980",
    "website": "",
    "developers": "Rifaï Games Studio",
    "publishers": "Rifaï Games Studio",
    "categories": "Single-player;Multi-player;Full controller support;Steam Workshop;Includes level editor;Family Sharing",
    "genres": "Action;Indie",
    "tags": "Action;Indie",
    "latest_release_date": "December 2025",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 14,
    "steam_appid": 4043830,
    "name": "FuwaFuwa Survivors",
    "steam_url": "https://store.steampowered.com/app/4043830",
    "website": "",
    "developers": "開墾魂",
    "publishers": "開墾魂",
    "categories": "Single-player;Family Sharing",
    "genres": "Action;Indie",
    "tags": "Action;Indie",
    "latest_release_date": "January 2026",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 15,
    "steam_appid": 2394180,
    "name": "Primal Echo",
    "steam_url": "https://store.steampowered.com/app/2394180",
    "website": "",
    "developers": "Feral Flame Studios",
    "publishers": "Feral Flame Studios",
    "categories": "Single-player;Family Sharing",
    "genres": "Action;Adventure",
    "tags": "Action;Adventure",
    "latest_release_date": "Coming soon",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 16,
    "steam_appid": 4077240,
    "name": "怪獸公主SP：戀愛脈動",
    "steam_url": "https://store.steampowered.com/app/4077240",
    "website": "",
    "developers": "第四之壁 The Real Fourth Wall",
    "publishers": "第四之壁 The Real Fourth Wall",
    "categories": "Single-player;Family Sharing",
    "genres": "Casual;RPG",
    "tags": "Casual;RPG",
    "latest_release_date": "To be announced",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 17,
    "steam_appid": 4028510,
    "name": "King's Angel: Otome",
    "steam_url": "https://store.steampowered.com/app/4028510",
    "website": "",
    "developers": "Rolling Crown",
    "publishers": "Rolling Crown",
    "categories": "Single-player;Family Sharing",
    "genres": "Adventure;Casual;Simulation",
    "tags": "Adventure;Casual;Simulation",
    "latest_release_date": "To be announced",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  },
  {
    "id": 18,
    "steam_appid": 4036290,
    "name": "ORDER POINT",
    "steam_url": "https://store.steampowered.com/app/4036290",
    "website": "",
    "developers": "stormach",
    "publishers": "stormach",
    "categories": "Single-player;Steam Achievements;Full controller support;Camera Comfort;Playable without Timed Input;Stereo Sound;Stats;Family Sharing",
    "genres": "Indie;Simulation",
    "tags": "Indie;Simulation",
    "latest_release_date": "Coming soon",
    "latest_detection_stage": "public_unreleased",
    "latest_api_response_type": "full_details"
  }
];

// Mock游戏快照数据
export const mockSnapshots: GameSnapshot[] = mockGameSummaries.map((game, index) => {
  const csvGame = [{"type":"game","name":"Woolly","steam_appid":"3688970","developers":"Anneka Tran","publishers":"Anneka Tran","website":"","categories":"Single-player;Camera Comfort;Custom Volume Controls;Mouse Only Option;Save Anytime;Family Sharing","genres":"Casual;Indie","steam_url":"https://store.steampowered.com/app/3688970","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"November 2025","description":"Raise a flock of colourful sheep in this slow-paced idler. Look after your sheep, gather their fleeces and complete your collection.","supported_languages":"English","followers":"2","wishlists_est":"28","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Aberrate Inc.","steam_appid":"3620390","developers":"Aberrate Team","publishers":"Aberrate Team","website":"","categories":"Single-player;Partial Controller Support;Family Sharing","genres":"Casual;Indie","steam_url":"https://store.steampowered.com/app/3620390","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"To be announced","description":"Harness the power of aberration to split and reform reality at your command in this 3D, third-person, box and button puzzle game. exploit the unique rules Aberration imposes on the world in order to solve puzzles and progress through the towering building responsible for this scientific witchcraft.","supported_languages":"*;*","followers":"3","wishlists_est":"42","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Cozy Florist","steam_appid":"3868690","developers":"Two Cats Games","publishers":"Two Cats Games","website":"","categories":"Single-player;Steam Achievements;Full controller support;Family Sharing","genres":"Casual;Indie;Simulation;Strategy","steam_url":"https://store.steampowered.com/app/3868690","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"2026","description":"Bring your grandmother’s little flower shop back to life 🌷 Grow your own flowers, create lovely arrangements 💐 And slowly uncover the town’s mysterious story 🌙","supported_languages":"English;French;Italian;German;Spanish - Spain;Arabic;Simplified Chinese;Portuguese - Brazil;Bulgarian;Danish;Indonesian;Dutch;Finnish;Traditional Chinese;Japanese;Korean;Spanish - Latin America;Polish;Hungarian;Norwegian;Portuguese - Portugal;Romanian;Russian;Thai;Turkish;Ukrainian;Vietnamese;Greek;Czech;Swedish","followers":"1","wishlists_est":"14","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Nick's Saturday Morning Games","steam_appid":"2572310","developers":"Croaking Kero","publishers":"Croaking Kero","website":"","categories":"Single-player;Custom Volume Controls;Keyboard Only Option;Playable without Timed Input;Family Sharing","genres":"Casual;Indie;Early Access","steam_url":"https://store.steampowered.com/app/2572310","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Oct 31, 2025","description":"Small games to casually play when you wake up before everyone else on a Saturday morning.","supported_languages":"*;*","followers":"1","wishlists_est":"14","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Rockthesea","steam_appid":"2987560","developers":"Insexsity_team;Insexsity_team;Insexsity;Insexsity_team","publishers":"Demoartstudio.com;Demoartstudio;Demoartstudio","website":"https://www.demoartstudio.com","categories":"Single-player;Custom Volume Controls;Mouse Only Option;Save Anytime;Stereo Sound;Touch Only Option;Family Sharing","genres":"Action;Adventure;Indie;RPG;Early Access","steam_url":"https://store.steampowered.com/app/2987560","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Coming soon","description":"It's an adventure RPG with turn-based arcade battles, quests, team building, character customization, and travel. It also has a strong storytelling base. Currently, it has basic mechanics and gameplay options. It should be easy to play and have a nice view with an element of surprise.","supported_languages":"English;French;German;Spanish - Spain;Dutch;Portuguese - Portugal;Russian;Japanese;Danish;Italian;Czech;Finnish;Greek;Indonesian;Korean;Polish;Swedish;Simplified Chinese","followers":"2","wishlists_est":"22","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Vet Van Organizer","steam_appid":"3868740","developers":"Two Cats Games","publishers":"Two Cats Games","website":"","categories":"Single-player;Steam Achievements;Full controller support;Family Sharing","genres":"Casual;Indie","steam_url":"https://store.steampowered.com/app/3868740","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"2026","description":"Organize your vet van 🚐 Place 18 different animals correctly, keep rival species apart, and make room for every VIP friend! 💎🐾","supported_languages":"English;French;Italian;German;Spanish - Spain;Arabic;Simplified Chinese;Portuguese - Brazil;Bulgarian;Danish;Indonesian;Dutch;Finnish;Traditional Chinese;Japanese;Korean;Spanish - Latin America;Polish;Hungarian;Norwegian;Portuguese - Portugal;Romanian;Russian;Thai;Turkish;Ukrainian;Vietnamese;Greek;Czech;Swedish;Afrikaans;Amharic;Albanian;Assamese;Azerbaijani;Bangla;Basque;Belarusian;Bosnian;Dari;Armenian;Estonian;Persian;Filipino;Welsh;Galician;Gujarati;Georgian;Hausa;Hindi;Croatian;Kannada;Catalan;Kazakh;Quechua;K'iche';Khmer;Konkani;Kyrgyz;Latvian;Lithuanian;Luxembourgish;Macedonian;Malayalam;Malay;Maltese;Maori;Marathi;Mongolian;Nepali;Odia;Punjabi (Gurmukhi);Punjabi (Shahmukhi);Kinyarwanda;Sinhala;Sindhi;Slovak;Slovenian;Sorani;Sotho;Swahili;Serbian;Tajik;Tamil;Tatar;Telugu;Tigrinya;Tswana;Turkmen;Urdu;Uyghur;Valencian;Wolof;Xhosa;Yoruba;Zulu;Cherokee;Uzbek;Hebrew;Igbo;Irish;Scots;Icelandic","followers":"2","wishlists_est":"28","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Wonder Library : Prologue","steam_appid":"4062240","developers":"Areumdamda Media Lab","publishers":"Areumdamda Inc.","website":"https://www.wonderlibrarygame.com/","categories":"Single-player;Family Sharing","genres":"Action;Adventure;Casual;Indie;Simulation","steam_url":"https://store.steampowered.com/app/4062240","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Coming soon","description":"Wonder Library : Prologue begins as a girl named I awakens in a mysterious island library, her memories lost. Players explore a world where reality and imagination meet, embarking on a journey to rediscover what was forgotten. When she opens a book, a dreamlike adventure begins.","supported_languages":"*;, Korean;*;*","followers":"1","wishlists_est":"11","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"SHELLSTORM: The Great War","steam_appid":"3974220","developers":"Hypermad interactive","publishers":"Hypermad interactive","website":"https://www.hypermadinteractive.com/shellstorm","categories":"Single-player;Multi-player;PvP;Online PvP;Camera Comfort;Custom Volume Controls;Playable without Timed Input;Stereo Sound;Surround Sound;Family Sharing","genres":"Action;Indie;Simulation;Strategy","steam_url":"https://store.steampowered.com/app/3974220","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"To be announced","description":"SHELLSTORM™ unleashes satisfying tactical combat that redefines the RTS genre with destructible terrains, physics-driven interactions, and complex AI. Command infantry, artillery, tanks, and aircraft to overcome impossible odds on difficult missions, or play PvP battles and climb the leaderboards.","supported_languages":"*;*","followers":"7","wishlists_est":"77","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Rustmire","steam_appid":"3871310","developers":"MimicMimijeok","publishers":"MimicMimijeok","website":"","categories":"Single-player;Multi-player;PvP;Online PvP;Custom Volume Controls;Mouse Only Option;Save Anytime;Stereo Sound;Family Sharing","genres":"Adventure;Indie;Strategy","steam_url":"https://store.steampowered.com/app/3871310","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Q1 2026","description":"In this side-view pixel-art world, you captain a landship—survive by combat and scavenging, and grow your modular vessel into your own city. Among roaming cities and underground enclaves, records and wreckage hint at why people live this way… or how you become wreckage.","supported_languages":"English;Indonesian;Japanese;Korean;Spanish - Spain","followers":"1","wishlists_est":"12","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Backgammon Premium","steam_appid":"4072010","developers":"Spectrum.Games International Ltd","publishers":"Spectrum.Games International Ltd","website":"https://backgammonpremium.com/","categories":"Multi-player;PvP;Online PvP;Cross-Platform Multiplayer;In-App Purchases","genres":"Casual;Free To Play","steam_url":"https://store.steampowered.com/app/4072010","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Nov 17, 2025","description":"Classic backgammon with friends. Simple, clean design for timeless fun!","supported_languages":"English;Italian;Spanish - Spain;Greek;Portuguese - Portugal;Russian;Turkish;French;German;Arabic","followers":"1","wishlists_est":"14","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Face Interrogation","steam_appid":"4059210","developers":"ODale Studios","publishers":"ODale Studios","website":"","categories":"Single-player;Steam Achievements;Family Sharing","genres":"Action;Adventure;Simulation","steam_url":"https://store.steampowered.com/app/4059210","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"2026","description":"Become the detective. Try and outsmart the killer by picking the right way forward. It's up to you to figure out clues, takes notes, then use your Command Computer to unlock and confirm core behaviors in the subject. Once you understand him, you may solve the case. Or you might just end the world.","supported_languages":"*;*","followers":"","wishlists_est":"","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Virtual Perspective","steam_appid":"3653230","developers":"Coreplix Studios","publishers":"Coreplix Studios","website":"","categories":"Single-player;Full controller support;Family Sharing","genres":"Action","steam_url":"https://store.steampowered.com/app/3653230","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"To be announced","description":"Virtual Perspective is a first-person puzzle-action platformer where you manipulate Power Cells using your perspective to solve spatial challenges.","supported_languages":"*;, French, Italian, German, Spanish - Spain, Dutch, Swedish, Bulgarian, Czech, Danish, Japanese, Simplified Chinese;*","followers":"3","wishlists_est":"33","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Draw & Play !","steam_appid":"4047980","developers":"Rifaï Games Studio","publishers":"Rifaï Games Studio","website":"","categories":"Single-player;Multi-player;Full controller support;Steam Workshop;Includes level editor;Family Sharing","genres":"Action;Indie","steam_url":"https://store.steampowered.com/app/4047980","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"December 2025","description":"Draw your platforms, add doodle enemies, and take on community levels!","supported_languages":"English","followers":"4","wishlists_est":"44","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"FuwaFuwa Survivors","steam_appid":"4043830","developers":"開墾魂","publishers":"開墾魂","website":"","categories":"Single-player;Family Sharing","genres":"Action;Indie","steam_url":"https://store.steampowered.com/app/4043830","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"January 2026","description":"Survive with your fluffy companions! FuwaFuwa Survivors is a survivor-style action roguelite game. Control cute animals to fight through swarming enemies and defeat powerful bosses in tight 15minute run. Level up skills and combine skill evolutions with 30+ enchantments to forge your unique builds!","supported_languages":"English;Simplified Chinese;Traditional Chinese;Japanese","followers":"1","wishlists_est":"11","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"Primal Echo","steam_appid":"2394180","developers":"Feral Flame Studios","publishers":"Feral Flame Studios","website":"","categories":"Single-player;Family Sharing","genres":"Action;Adventure","steam_url":"https://store.steampowered.com/app/2394180","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Coming soon","description":"Escape from an alien megastructure that harbors an ancient ecosystem. Climb, fight and bite your way through a retro-inspired metroidvania that fuses survival with 3D action-platformers.","supported_languages":"*;*","followers":"2","wishlists_est":"22","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"怪獸公主SP：戀愛脈動","steam_appid":"4077240","developers":"第四之壁 The Real Fourth Wall","publishers":"第四之壁 The Real Fourth Wall","website":"","categories":"Single-player;Family Sharing","genres":"Casual;RPG","steam_url":"https://store.steampowered.com/app/4077240","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"To be announced","description":"Secret Pulse is a realistic visual novel.","supported_languages":"*;, Simplified Chinese;*","followers":"9","wishlists_est":"126","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"King's Angel: Otome","steam_appid":"4028510","developers":"Rolling Crown","publishers":"Rolling Crown","website":"","categories":"Single-player;Family Sharing","genres":"Adventure;Casual;Simulation","steam_url":"https://store.steampowered.com/app/4028510","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"To be announced","description":"Travel through alternate timelines, solve the mystery and find love in a cursed kingdom!","supported_languages":"English","followers":"12","wishlists_est":"144","wishlist_rank":"","discovery_date":"2025-10-13"},{"type":"game","name":"ORDER POINT","steam_appid":"4036290","developers":"stormach","publishers":"stormach","website":"","categories":"Single-player;Steam Achievements;Full controller support;Camera Comfort;Playable without Timed Input;Stereo Sound;Stats;Family Sharing","genres":"Indie;Simulation","steam_url":"https://store.steampowered.com/app/4036290","detection_stage":"public_unreleased","api_response_type":"full_details","potential_duplicate":"False","release_date":"Coming soon","description":"ORDER POINT is a horror game about working at a package pickup station. On a winter night, you serve unsettling customers. Mysterious visitors create an ominous atmosphere. Be careful — not everyone can be trusted.","supported_languages":"English;Russian","followers":"","wishlists_est":"","wishlist_rank":"","discovery_date":"2025-10-13"}];
  const gameData = csvGame[index];
  
  return {
    id: game.id,
    game: game,
    batch_id: 100,
    detection_stage: game.latest_detection_stage,
    api_response_type: game.latest_api_response_type,
    potential_duplicate: gameData.potential_duplicate === 'True',
    discovery_date: gameData.discovery_date || "2025-10-13",
    ingested_for_date: "2025-10-13",
    release_date_raw: game.latest_release_date,
    description: gameData.description || "An exciting new game experience awaits you!",
    supported_languages: gameData.supported_languages || "English",
    followers: parseInt(gameData.followers) || null,
    wishlists_est: parseInt(gameData.wishlists_est) || null,
    wishlist_rank: gameData.wishlist_rank ? parseInt(gameData.wishlist_rank) : null,
    source_categories: gameData.categories || "",
    source_genres: gameData.genres || "",
    source_tags: gameData.genres || ""
  };
});

// 导出mock API响应
export const mockApiResponse = {
  count: mockSnapshots.length,
  next: null,
  previous: null,
  results: mockSnapshots
};

console.log(`📦 Mock数据已加载: ${mockSnapshots.length} 个游戏`);




