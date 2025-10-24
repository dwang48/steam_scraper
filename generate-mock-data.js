#!/usr/bin/env node
/**
 * 从CSV文件生成Mock数据的脚本
 * 使用方法: node generate-mock-data.js
 */

const fs = require('fs');
const path = require('path');

// CSV文件路径
const csvPath = path.join(__dirname, 'backend/exports copy/new_games_2025-10-13.csv');
const outputPath = path.join(__dirname, 'frontend/src/mocks/mockData.ts');

console.log('📊 正在从CSV生成Mock数据...\n');

// 读取CSV文件
const csvContent = fs.readFileSync(csvPath, 'utf-8');
const lines = csvContent.split('\n').filter(line => line.trim());

// 解析CSV（简单的逗号分隔，处理引号）
function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  
  return result.map(field => field.trim());
}

// 解析表头
const headers = parseCSVLine(lines[0]);
console.log('📋 CSV列:', headers.join(', '));

// 解析数据行
const games = [];
for (let i = 1; i < Math.min(lines.length, 21); i++) { // 最多取20个游戏
  const values = parseCSVLine(lines[i]);
  const game = {};
  
  headers.forEach((header, index) => {
    game[header] = values[index] || '';
  });
  
  // 只添加type为game的记录
  if (game.type === 'game' && game.name && game.steam_appid) {
    games.push(game);
  }
}

console.log(`✅ 成功解析 ${games.length} 个游戏\n`);

// 生成TypeScript代码
const tsCode = `// Mock游戏数据 - 从CSV自动生成
// 生成时间: ${new Date().toISOString()}
// 数据源: backend/exports copy/new_games_2025-10-13.csv

import { GameSnapshot, GameSummary } from "../types";

// Mock游戏概要数据
const mockGameSummaries: GameSummary[] = ${JSON.stringify(
  games.map((game, index) => ({
    id: index + 1,
    steam_appid: parseInt(game.steam_appid) || 0,
    name: game.name,
    steam_url: game.steam_url,
    website: game.website,
    developers: game.developers,
    publishers: game.publishers,
    categories: game.categories,
    genres: game.genres,
    tags: game.genres, // 使用genres作为tags
    latest_release_date: game.release_date,
    latest_detection_stage: game.detection_stage,
    latest_api_response_type: game.api_response_type
  })),
  null,
  2
)};

// Mock游戏快照数据
export const mockSnapshots: GameSnapshot[] = mockGameSummaries.map((game, index) => {
  const csvGame = ${JSON.stringify(games)};
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

console.log(\`📦 Mock数据已加载: \${mockSnapshots.length} 个游戏\`);
`;

// 写入文件
fs.writeFileSync(outputPath, tsCode, 'utf-8');

console.log('✨ 生成完成！');
console.log(`📁 输出文件: ${outputPath}`);
console.log(`\n🎮 包含的游戏:`);
games.forEach((game, index) => {
  console.log(`   ${index + 1}. ${game.name} (AppID: ${game.steam_appid})`);
});
console.log('\n✅ 完成！现在可以运行 npm run dev:demo 测试');





