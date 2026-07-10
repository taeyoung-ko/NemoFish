<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <!-- Step 01: 模拟实例 -->
      <div class="step-card" :class="{ 'active': phase === 0, 'completed': phase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">{{ $t('step2.simInstanceInit') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 0" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else class="badge processing">{{ $t('step2.initializing') }}</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">
            {{ $t('step2.simInstanceDesc') }}
          </p>

          <div v-if="simulationId" class="info-card">
            <div class="info-row">
              <span class="info-label">Project ID</span>
              <span class="info-value mono">{{ projectData?.project_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Graph ID</span>
              <span class="info-value mono">{{ projectData?.graph_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Simulation ID</span>
              <span class="info-value mono">{{ simulationId }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Task ID</span>
              <span class="info-value mono">{{ taskId || $t('step2.asyncTaskDone') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: 生成 Agent 人设 -->
      <div class="step-card" :class="{ 'active': phase === 1, 'completed': phase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">{{ $t('step2.generateAgentPersona') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 1" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 1" class="badge processing">{{ prepareProgress }}%</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('step2.generateAgentPersonaDesc') }}
          </p>

          <!-- 에이전트 수 설정 (그래프 생성 후, 추천값 자동 · 수정 가능) -->
          <div v-if="phase === 0" class="agent-count-setup">
            <div class="count-row">
              <label class="count-label">{{ $t('step2.agentCountLabel') }}</label>
              <input class="count-input" type="number" min="1" max="1000" v-model.number="nemotronCount" />
              <span class="count-hint" v-if="autoCount">{{ $t('step2.agentCountRecommended', { n: autoCount }) }}</span>
            </div>

            <!-- 샘플링 방식: 전체 랜덤 / 조건 필터 후 랜덤 -->
            <div v-if="facetsAvailable" class="sampling-mode">
              <span class="mode-title">{{ $t('step2.filterModeLabel') }}</span>
              <div class="mode-tabs">
                <button
                  class="mode-tab"
                  :class="{ active: filterMode === 'all' }"
                  @click="filterMode = 'all'"
                >{{ $t('step2.filterAll') }}</button>
                <button
                  class="mode-tab"
                  :class="{ active: filterMode === 'filter' }"
                  @click="filterMode = 'filter'"
                >{{ $t('step2.filterByCondition') }}</button>
              </div>
            </div>

            <!-- 조건 필터 패널 -->
            <div v-if="facetsAvailable && filterMode === 'filter'" class="filter-panel">
              <!-- 범주형 필드들 -->
              <div v-for="field in categoricalFields" :key="field.key" class="filter-group">
                <div class="filter-group-header">
                  <span class="filter-group-title">{{ fieldLabel(field.key) }}</span>
                  <span v-if="selectedFilters[field.key]?.length" class="filter-group-count">
                    {{ selectedFilters[field.key].length }}
                  </span>
                </div>
                <div class="filter-chips">
                  <button
                    v-for="opt in field.values"
                    :key="opt.value"
                    class="filter-chip"
                    :class="{ selected: selectedFilters[field.key]?.includes(opt.value) }"
                    @click="toggleFilter(field.key, opt.value)"
                  >
                    {{ valueLabel(field.key, opt.value) }}
                    <span class="chip-count">{{ opt.count }}</span>
                  </button>
                </div>
              </div>

              <!-- 나이 범위 -->
              <div v-if="ageFacet" class="filter-group">
                <div class="filter-group-header">
                  <label class="filter-group-title age-toggle">
                    <input type="checkbox" v-model="ageEnabled" />
                    {{ $t('step2.filterAgeRange') }}
                  </label>
                </div>
                <div v-if="ageEnabled" class="age-range-row">
                  <input class="age-input" type="number" :min="ageFacet.min" :max="ageFacet.max" v-model.number="ageMin" />
                  <span class="age-sep">~</span>
                  <input class="age-input" type="number" :min="ageFacet.min" :max="ageFacet.max" v-model.number="ageMax" />
                  <span class="age-unit">{{ $t('step2.yearsOld') }}</span>
                </div>
              </div>

              <!-- 매칭 미리보기 -->
              <div class="filter-preview" :class="{ warn: matchedCount !== null && matchedCount < nemotronCount }">
                <span class="preview-text">
                  <template v-if="matchedCount === null">{{ $t('step2.filterCounting') }}</template>
                  <template v-else-if="matchedCount < nemotronCount">
                    {{ $t('step2.filterMatchWarning', { matched: matchedCount, count: nemotronCount }) }}
                  </template>
                  <template v-else>
                    {{ $t('step2.filterMatchPreview', { matched: matchedCount, count: nemotronCount }) }}
                  </template>
                </span>
                <button class="filter-clear" @click="clearFilters">{{ $t('step2.filterClear') }}</button>
              </div>
            </div>

            <button class="generate-btn" @click="beginGeneration" :disabled="!nemotronCount || nemotronCount < 1">
              {{ $t('step2.startGenerate') }}
            </button>
          </div>

          <!-- Profiles Stats -->
          <div v-if="profiles.length > 0" class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ profiles.length }}</span>
              <span class="stat-label">{{ $t('step2.currentAgentCount') }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ totalTopicsCount }}</span>
              <span class="stat-label">{{ $t('step2.relatedTopicsCount') }}</span>
            </div>
          </div>

          <!-- Profiles List Preview -->
          <div v-if="profiles.length > 0" class="profiles-preview">
            <div class="preview-header">
              <span class="preview-title">{{ $t('step2.generatedAgentPersonas') }}</span>
            </div>
            <div class="profiles-list">
              <div 
                v-for="(profile, idx) in profiles" 
                :key="idx" 
                class="profile-card"
                @click="selectProfile(profile)"
              >
                <div class="profile-header">
                  <span class="profile-realname">{{ profile.username || 'Unknown' }}</span>
                  <span class="profile-username">@{{ profile.name || `agent_${idx}` }}</span>
                </div>
                <div class="profile-meta">
                  <span class="profile-profession">{{ profile.profession || $t('step2.unknownProfession') }}</span>
                </div>
                <p class="profile-bio">{{ profile.bio || $t('step2.noBio') }}</p>
                <div v-if="profile.interested_topics?.length" class="profile-topics">
                  <span 
                    v-for="topic in profile.interested_topics.slice(0, 3)" 
                    :key="topic" 
                    class="topic-tag"
                  >{{ topic }}</span>
                  <span v-if="profile.interested_topics.length > 3" class="topic-more">
                    +{{ profile.interested_topics.length - 3 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: 生成双平台模拟配置 -->
      <div class="step-card" :class="{ 'active': phase === 2, 'completed': phase > 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">{{ $t('step2.dualPlatformConfig') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 2" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 2" class="badge processing">{{ $t('step2.generating') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('step2.dualPlatformConfigDesc') }}
          </p>
          
          <!-- Config Preview -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <!-- 时间配置 -->
            <div class="config-block">
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.simulationDuration') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.total_simulation_hours || '-' }} {{ $t('common.hours') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.roundDuration') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.minutes_per_round || '-' }} {{ $t('common.minutes') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.totalRounds') }}</span>
                  <span class="config-item-value">{{ Math.floor((simulationConfig.time_config?.total_simulation_hours * 60 / simulationConfig.time_config?.minutes_per_round)) || '-' }} {{ $t('common.rounds') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.activePerHour') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.agents_per_hour_min }}-{{ simulationConfig.time_config?.agents_per_hour_max }}</span>
                </div>
              </div>
              <div class="time-periods">
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.peakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.peak_hours?.join(':00, ') }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.peak_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.workHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.work_hours?.[0] }}:00-{{ simulationConfig.time_config?.work_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.work_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.morningHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.morning_hours?.[0] }}:00-{{ simulationConfig.time_config?.morning_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.morning_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.offPeakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.off_peak_hours?.[0] }}:00-{{ simulationConfig.time_config?.off_peak_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.off_peak_activity_multiplier }}</span>
                </div>
              </div>
            </div>

            <!-- Agent 配置 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.agentConfig') }}</span>
                <span class="config-block-badge">{{ simulationConfig.agent_configs?.length || 0 }} {{ $t('common.items') }}</span>
              </div>
              <div class="agents-cards">
                <div 
                  v-for="agent in simulationConfig.agent_configs" 
                  :key="agent.agent_id" 
                  class="agent-card"
                >
                  <!-- 卡片头部 -->
                  <div class="agent-card-header">
                    <div class="agent-identity">
                      <span class="agent-id">Agent {{ agent.agent_id }}</span>
                      <span class="agent-name">{{ agent.entity_name }}</span>
                    </div>
                    <div class="agent-tags">
                      <span class="agent-type">{{ agent.entity_type }}</span>
                      <span class="agent-stance" :class="'stance-' + agent.stance">{{ agent.stance }}</span>
                    </div>
                  </div>
                  
                  <!-- 活跃时间轴 -->
                  <div class="agent-timeline">
                    <span class="timeline-label">{{ $t('step2.activeTimePeriod') }}</span>
                    <div class="mini-timeline">
                      <div 
                        v-for="hour in 24" 
                        :key="hour - 1" 
                        class="timeline-hour"
                        :class="{ 'active': agent.active_hours?.includes(hour - 1) }"
                        :title="`${hour - 1}:00`"
                      ></div>
                    </div>
                    <div class="timeline-marks">
                      <span>0</span>
                      <span>6</span>
                      <span>12</span>
                      <span>18</span>
                      <span>24</span>
                    </div>
                  </div>

                  <!-- 行为参数 -->
                  <div class="agent-params">
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.postsPerHour') }}</span>
                        <span class="param-value">{{ agent.posts_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.commentsPerHour') }}</span>
                        <span class="param-value">{{ agent.comments_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.responseDelay') }}</span>
                        <span class="param-value">{{ agent.response_delay_min }}-{{ agent.response_delay_max }}min</span>
                      </div>
                    </div>
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.activityLevel') }}</span>
                        <span class="param-value with-bar">
                          <span class="mini-bar" :style="{ width: (agent.activity_level * 100) + '%' }"></span>
                          {{ (agent.activity_level * 100).toFixed(0) }}%
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.sentimentBias') }}</span>
                        <span class="param-value" :class="agent.sentiment_bias > 0 ? 'positive' : agent.sentiment_bias < 0 ? 'negative' : 'neutral'">
                          {{ agent.sentiment_bias > 0 ? '+' : '' }}{{ agent.sentiment_bias?.toFixed(1) }}
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.influenceWeight') }}</span>
                        <span class="param-value highlight">{{ agent.influence_weight?.toFixed(1) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 平台配置 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.recommendAlgoConfig') }}</span>
              </div>
              <div class="platforms-grid">
                <div v-if="simulationConfig.twitter_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">{{ $t('step2.platform1Name') }}</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.recencyWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.echoChamberStrength') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="simulationConfig.reddit_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">{{ $t('step2.platform2Name') }}</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.recencyWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.echoChamberStrength') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- LLM 配置推理 -->
            <div v-if="simulationConfig.generation_reasoning" class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.llmConfigReasoning') }}</span>
              </div>
              <div class="reasoning-content">
                <div 
                  v-for="(reason, idx) in simulationConfig.generation_reasoning.split('|').slice(0, 2)" 
                  :key="idx" 
                  class="reasoning-item"
                >
                  <p class="reasoning-text">{{ reason.trim() }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 04: 初始激活编排 -->
      <div class="step-card" :class="{ 'active': phase === 3, 'completed': phase > 3 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">{{ $t('step2.initialActivation') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 3" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 3" class="badge processing">{{ $t('step2.orchestrating') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('step2.initialActivationDesc') }}
          </p>

          <div v-if="simulationConfig?.event_config" class="orchestration-content">
            <!-- 叙事方向 -->
            <div class="narrative-box">
              <span class="box-label narrative-label">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="special-icon">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M16.24 7.76L14.12 14.12L7.76 16.24L9.88 9.88L16.24 7.76Z" fill="url(#paint0_linear)" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <defs>
                    <linearGradient id="paint0_linear" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#1C1C1C"/>
                      <stop offset="1" stop-color="#5F5F5D"/>
                    </linearGradient>
                  </defs>
                </svg>
                {{ $t('step2.narrativeDirection') }}
              </span>
              <p class="narrative-text">{{ simulationConfig.event_config.narrative_direction }}</p>
            </div>

            <!-- 热点话题 -->
            <div class="topics-section">
              <span class="box-label">{{ $t('step2.initialHotTopics') }}</span>
              <div class="hot-topics-grid">
                <span v-for="topic in simulationConfig.event_config.hot_topics" :key="topic" class="hot-topic-tag">
                  # {{ topic }}
                </span>
              </div>
            </div>

            <!-- 初始帖子流 -->
            <div class="initial-posts-section">
              <span class="box-label">{{ $t('step2.initialActivationSeq', { count: simulationConfig.event_config.initial_posts.length }) }}</span>
              <div class="posts-timeline">
                <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="timeline-item">
                  <div class="timeline-marker"></div>
                  <div class="timeline-content">
                    <div class="post-header">
                      <span class="post-role">{{ post.poster_type }}</span>
                      <span class="post-agent-info">
                        <span class="post-id">Agent {{ post.poster_agent_id }}</span>
                        <span class="post-username">@{{ getAgentUsername(post.poster_agent_id) }}</span>
                      </span>
                    </div>
                    <p class="post-text">{{ post.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 05: 准备完成 -->
      <div class="step-card" :class="{ 'active': phase === 4 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">05</span>
            <span class="step-title">{{ $t('step2.setupComplete') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase >= 4" class="badge processing">{{ $t('step1.inProgress') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/start</p>
          <p class="description">{{ $t('step2.setupCompleteDesc') }}</p>
          
          <!-- 模拟轮数配置 - 只有在配置生成完成且轮数计算出来后才显示 -->
          <div v-if="simulationConfig && autoGeneratedRounds" class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">{{ $t('step2.roundsConfig') }}</span>
                <span class="section-desc">{{ $t('step2.roundsConfigDesc', { hours: simulationConfig?.time_config?.total_simulation_hours || '-', minutesPerRound: simulationConfig?.time_config?.minutes_per_round || '-' }) }}</span>
              </div>
              <label class="switch-control">
                <input type="checkbox" v-model="useCustomRounds">
                <span class="switch-track"></span>
                <span class="switch-label">{{ $t('step2.customToggle') }}</span>
              </label>
            </div>
            
            <Transition name="fade" mode="out-in">
              <div v-if="useCustomRounds" class="rounds-content custom" key="custom">
                <div class="slider-display">
                  <div class="slider-main-value">
                    <span class="val-num">{{ customMaxRounds }}</span>
                    <span class="val-unit">{{ $t('step2.roundsUnit') }}</span>
                  </div>
                  <div class="slider-meta-info">
                    <span>{{ $t('step2.estimatedDuration', { minutes: Math.round(customMaxRounds * 0.6) }) }}</span>
                  </div>
                </div>

                <div class="range-wrapper">
                  <input 
                    type="range" 
                    v-model.number="customMaxRounds" 
                    min="10" 
                    :max="autoGeneratedRounds"
                    step="5"
                    class="minimal-slider"
                    :style="{ '--percent': ((customMaxRounds - 10) / (autoGeneratedRounds - 10)) * 100 + '%' }"
                  />
                  <div class="range-marks">
                    <span>10</span>
                    <span 
                      class="mark-recommend" 
                      :class="{ active: customMaxRounds === 40 }"
                      @click="customMaxRounds = 40"
                      :style="{ position: 'absolute', left: `calc(${(40 - 10) / (autoGeneratedRounds - 10) * 100}% - 30px)` }"
                    >{{ $t('step2.recommendedRounds', { rounds: 40 }) }}</span>
                    <span>{{ autoGeneratedRounds }}</span>
                  </div>
                </div>
              </div>
              
              <div v-else class="rounds-content auto" key="auto">
                <div class="auto-info-card">
                  <div class="auto-value">
                    <span class="val-num">{{ autoGeneratedRounds }}</span>
                    <span class="val-unit">{{ $t('step2.roundsUnit') }}</span>
                  </div>
                  <div class="auto-content">
                    <div class="auto-meta-row">
                      <span class="duration-badge">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        {{ $t('step2.estimatedDurationFull', { minutes: Math.round(autoGeneratedRounds * 0.6) }) }}
                      </span>
                    </div>
                    <div class="auto-desc">
                      <p class="highlight-tip" @click="useCustomRounds = true">{{ $t('step2.customTip') }} ➝</p>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <div class="action-group dual">
            <button 
              class="action-btn secondary"
              @click="$emit('go-back')"
            >
              ← {{ $t('step2.backToGraphBuild') }}
            </button>
            <button 
              class="action-btn primary"
              :disabled="phase < 4"
              @click="handleStartSimulation"
            >
              {{ $t('step2.startDualWorldSim') }} ➝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div v-if="selectedProfile" class="profile-modal-overlay" @click.self="selectedProfile = null">
        <div class="profile-modal">
          <div class="modal-header">
          <div class="modal-header-info">
            <div class="modal-name-row">
              <span class="modal-realname">{{ selectedProfile.name }}</span>
              <span class="modal-username">@{{ selectedProfile.username }}</span>
            </div>
            <span class="modal-profession">{{ selectedProfile.profession }}</span>
          </div>
          <button class="close-btn" @click="selectedProfile = null">×</button>
        </div>
        
        <div class="modal-body">
          <!-- 기본 정보 (Nemotron 컬럼별) -->
          <div class="modal-info-grid">
            <div class="info-item">
              <span class="info-label">{{ $t('step2.profileModalAge') }}</span>
              <span class="info-value">{{ selectedProfile.age || '-' }} {{ $t('step2.yearsOld') }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('step2.profileModalGender') }}</span>
              <span class="info-value">{{ { male: $t('step2.genderMale'), female: $t('step2.genderFemale'), other: $t('step2.genderOther') }[selectedProfile.gender] || selectedProfile.gender }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.profession">
              <span class="info-label">{{ $t('step2.profileModalProfession') }}</span>
              <span class="info-value">{{ selectedProfile.profession }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.province || selectedProfile.district">
              <span class="info-label">{{ $t('step2.profileModalRegion') }}</span>
              <span class="info-value">{{ (selectedProfile.district || selectedProfile.province || '').replace('-', ' ') }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.education_level">
              <span class="info-label">{{ $t('step2.profileModalEducation') }}</span>
              <span class="info-value">{{ selectedProfile.education_level }}{{ selectedProfile.bachelors_field && selectedProfile.bachelors_field !== '해당없음' ? ' · ' + selectedProfile.bachelors_field : '' }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.marital_status">
              <span class="info-label">{{ $t('step2.profileModalMarital') }}</span>
              <span class="info-value">{{ selectedProfile.marital_status }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.family_type">
              <span class="info-label">{{ $t('step2.profileModalFamily') }}</span>
              <span class="info-value">{{ selectedProfile.family_type }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.housing_type">
              <span class="info-label">{{ $t('step2.profileModalHousing') }}</span>
              <span class="info-value">{{ selectedProfile.housing_type }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.military_status && selectedProfile.military_status !== '해당없음'">
              <span class="info-label">{{ $t('step2.profileModalMilitary') }}</span>
              <span class="info-value">{{ selectedProfile.military_status }}</span>
            </div>
            <div class="info-item" v-if="selectedProfile.country">
              <span class="info-label">{{ $t('step2.profileModalCountry') }}</span>
              <span class="info-value">{{ selectedProfile.country }}</span>
            </div>
          </div>

          <!-- 한 줄 소개 -->
          <div class="modal-section">
            <span class="section-label">{{ $t('step2.profileModalBio') }}</span>
            <p class="section-bio">{{ selectedProfile.bio || $t('step2.noBio') }}</p>
          </div>

          <!-- 전문 스킬 -->
          <div class="modal-section" v-if="selectedProfile.skills?.length">
            <span class="section-label">{{ $t('step2.profileModalSkills') }}</span>
            <div class="topics-grid">
              <span v-for="s in selectedProfile.skills" :key="s" class="topic-item skill-item">{{ s }}</span>
            </div>
          </div>

          <!-- 관심사 -->
          <div class="modal-section" v-if="selectedProfile.interested_topics?.length">
            <span class="section-label">{{ $t('step2.profileModalTopics') }}</span>
            <div class="topics-grid">
              <span v-for="topic in selectedProfile.interested_topics" :key="topic" class="topic-item">{{ topic }}</span>
            </div>
          </div>

          <!-- 상세 페르소나 -->
          <div class="modal-section" v-if="selectedProfile.persona">
            <span class="section-label">{{ $t('step2.profileModalPersona') }}</span>
            <div class="persona-content">
              <p class="section-persona">{{ selectedProfile.persona }}</p>
            </div>
          </div>
        </div>
      </div>
      </div>
    </Transition>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  prepareSimulation,
  getPrepareStatus,
  getSimulationProfilesRealtime,
  getSimulationConfig,
  getSimulationConfigRealtime,
  getNemotronFacets,
  countNemotronMatching
} from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  simulationId: String,  // 从父组件传入
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

// State
const phase = ref(0) // 0: 初始化, 1: 生成人设, 2: 生成配置, 3: 完成
const taskId = ref(null)
const prepareProgress = ref(0)
const currentStage = ref('')
const progressMessage = ref('')
const profiles = ref([])
const entityTypes = ref([])
const expectedTotal = ref(null)
const nemotronCount = ref(20)      // 생성할 에이전트 수 (입력값)
const autoCount = ref(null)        // 그래프 엔티티 수 = 추천/기본값

// ===== Nemotron 조건 필터 (필터 후 랜덤) =====
const facets = ref(null)               // /nemotron/facets 응답
const filterMode = ref('all')          // 'all'(전체 랜덤) | 'filter'(조건 필터)
const selectedFilters = reactive({})   // { <field>: [선택값...] }
const ageEnabled = ref(false)
const ageMin = ref(null)
const ageMax = ref(null)
const matchedCount = ref(null)         // 조건 만족 표본 수(미리보기). null=집계중
let countTimer = null

const facetsAvailable = computed(() => !!facets.value?.available)
const ageFacet = computed(() => facets.value?.fields?.age || null)
// 범주형 필드 목록(선언 순서 유지, age 제외)
const categoricalFields = computed(() => {
  const f = facets.value?.fields || {}
  return Object.keys(f)
    .filter(k => f[k].type === 'categorical')
    .map(k => ({ key: k, values: f[k].values }))
})

const FIELD_LABEL_KEYS = {
  gender: 'step2.profileModalGender',
  province: 'step2.profileModalRegion',
  education_level: 'step2.profileModalEducation',
  marital_status: 'step2.profileModalMarital',
  military_status: 'step2.profileModalMilitary',
  family_type: 'step2.profileModalFamily',
  housing_type: 'step2.profileModalHousing',
  age: 'step2.profileModalAge',
}
const fieldLabel = (key) => FIELD_LABEL_KEYS[key] ? t(FIELD_LABEL_KEYS[key]) : key
const valueLabel = (key, val) => {
  if (key === 'gender') {
    return { male: t('step2.genderMale'), female: t('step2.genderFemale'), other: t('step2.genderOther') }[val] || val
  }
  return val
}

const toggleFilter = (field, value) => {
  if (!Array.isArray(selectedFilters[field])) selectedFilters[field] = []
  const arr = selectedFilters[field]
  const i = arr.indexOf(value)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(value)
}

const clearFilters = () => {
  Object.keys(selectedFilters).forEach(k => { selectedFilters[k] = [] })
  ageEnabled.value = false
  if (ageFacet.value) { ageMin.value = ageFacet.value.min; ageMax.value = ageFacet.value.max }
}

// 요청에 실어보낼 필터 객체(빈 조건은 제외). filter 모드가 아니거나 조건 없으면 null.
const activeFilters = computed(() => {
  if (filterMode.value !== 'filter') return null
  const out = {}
  for (const [k, arr] of Object.entries(selectedFilters)) {
    if (Array.isArray(arr) && arr.length) out[k] = [...arr]
  }
  if (ageEnabled.value && ageMin.value != null && ageMax.value != null) {
    out.age = { min: Math.min(ageMin.value, ageMax.value), max: Math.max(ageMin.value, ageMax.value) }
  }
  return Object.keys(out).length ? out : null
})

// 필터 변경 시 매칭 수 실시간 조회(디바운스)
watch(activeFilters, (f) => {
  if (filterMode.value !== 'filter') { matchedCount.value = null; return }
  matchedCount.value = null
  if (countTimer) clearTimeout(countTimer)
  countTimer = setTimeout(async () => {
    try {
      const res = await countNemotronMatching(f)
      if (res.success && res.data) matchedCount.value = res.data.matched
    } catch (e) { /* 무시 */ }
  }, 300)
}, { deep: true })

watch(filterMode, (m) => {
  if (m === 'filter' && matchedCount.value === null) {
    // 조건 없이 진입하면 전체 수를 미리보기로
    matchedCount.value = facets.value?.total ?? null
  }
})
const simulationConfig = ref(null)
const selectedProfile = ref(null)
const showProfilesDetail = ref(true)

// 日志去重：记录上一次输出的关键信息
let lastLoggedMessage = ''
let lastLoggedProfileCount = 0
let lastLoggedConfigStage = ''

// 模拟轮数配置
const useCustomRounds = ref(false) // 默认使用自动配置轮数
const customMaxRounds = ref(40)   // 默认推荐40轮

// Watch stage to update phase
watch(currentStage, (newStage) => {
  if (newStage === '生成Agent人设' || newStage === 'generating_profiles') {
    phase.value = 1
  } else if (newStage === '生成模拟配置' || newStage === 'generating_config') {
    phase.value = 2
    // 进入配置生成阶段，开始轮询配置
    if (!configTimer) {
      addLog(t('log.startGeneratingConfig'))
      startConfigPolling()
    }
  } else if (newStage === '准备模拟脚本' || newStage === 'copying_scripts') {
    phase.value = 2 // 仍属于配置阶段
  }
})

// 从配置中计算自动生成的轮数（不使用硬编码默认值）
const autoGeneratedRounds = computed(() => {
  if (!simulationConfig.value?.time_config) {
    return null // 配置未生成时返回 null
  }
  const totalHours = simulationConfig.value.time_config.total_simulation_hours
  const minutesPerRound = simulationConfig.value.time_config.minutes_per_round
  if (!totalHours || !minutesPerRound) {
    return null // 配置数据不完整时返回 null
  }
  const calculatedRounds = Math.floor((totalHours * 60) / minutesPerRound)
  // 确保最大轮数不小于40（推荐值），避免滑动条范围异常
  return Math.max(calculatedRounds, 40)
})

// Polling timer
let pollTimer = null
let profilesTimer = null
let configTimer = null

// Computed
const displayProfiles = computed(() => {
  if (showProfilesDetail.value) {
    return profiles.value
  }
  return profiles.value.slice(0, 6)
})

// 根据agent_id获取对应的username
const getAgentUsername = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    const profile = profiles.value[agentId]
    return profile?.username || `agent_${agentId}`
  }
  return `agent_${agentId}`
}

// 计算所有人设的关联话题总数
const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0)
  }, 0)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// 处理开始模拟按钮点击
const handleStartSimulation = () => {
  // 构建传递给父组件的参数
  const params = {}
  
  if (useCustomRounds.value) {
    // 用户自定义轮数，传递 max_rounds 参数
    params.maxRounds = customMaxRounds.value
    addLog(t('log.startSimCustomRounds', { rounds: customMaxRounds.value }))
  } else {
    // 用户选择保持自动生成的轮数，不传递 max_rounds 参数
    addLog(t('log.startSimAutoRounds', { rounds: autoGeneratedRounds.value }))
  }
  
  emit('next-step', params)
}

const truncateBio = (bio) => {
  if (bio.length > 80) {
    return bio.substring(0, 80) + '...'
  }
  return bio
}

const selectProfile = (profile) => {
  selectedProfile.value = profile
}

// 엔티티 수 조회 → 추천/기본값 세팅 (생성은 버튼 클릭 시)
const fetchEntityCount = async () => {
  try {
    const res = await prepareSimulation({ simulation_id: props.simulationId, count_only: true })
    if (res.success && res.data?.count_only) {
      autoCount.value = res.data.expected_entities_count || null
      if (autoCount.value) nemotronCount.value = autoCount.value  // 첫 표시값 = 자동값
    }
  } catch (e) {
    // 무시: 조회 실패해도 기본값(20)으로 진행 가능
  }
}

// "페르소나 생성 시작" 버튼
const beginGeneration = () => {
  if (phase.value !== 0) return
  startPrepareSimulation()
}

// 준비(페르소나+설정 생성) 시작
const startPrepareSimulation = async () => {
  if (!props.simulationId) {
    addLog(t('log.errorMissingSimId'))
    emit('update-status', 'error')
    return
  }
  
  // 标记第一步完成，开始第二步
  phase.value = 1
  addLog(t('log.simInstanceCreated', { id: props.simulationId }))
  addLog(t('log.preparingSimEnv'))
  emit('update-status', 'processing')
  
  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5,
      // 입력한 에이전트 수 → Nemotron 샘플링 수
      nemotron_agent_count: nemotronCount.value,
      // 조건 필터(있으면 조건 만족 표본 중 랜덤). 전체 랜덤이면 null → 미전송.
      nemotron_filters: activeFilters.value
    })
    
    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog(t('log.detectedExistingPrep'))
        await loadPreparedData()
        return
      }
      
      taskId.value = res.data.task_id
      addLog(t('log.prepareTaskStarted'))
      addLog(t('log.prepareTaskId', { taskId: res.data.task_id }))
      
      // 立即设置预期Agent总数（从prepare接口返回值获取）
      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count
        addLog(t('log.zepEntitiesFound', { count: res.data.expected_entities_count }))
        if (res.data.entity_types && res.data.entity_types.length > 0) {
          addLog(t('log.entityTypes', { types: res.data.entity_types.join(', ') }))
        }
      }
      
      addLog(t('log.startPollingProgress'))
      // 开始轮询进度
      startPolling()
      // 开始实时获取 Profiles
      startProfilesPolling()
    } else {
      addLog(t('log.prepareFailed', { error: res.error || t('common.unknownError') }))
      emit('update-status', 'error')
    }
  } catch (err) {
    addLog(t('log.prepareException', { error: err.message }))
    emit('update-status', 'error')
  }
}

const startPolling = () => {
  pollTimer = setInterval(pollPrepareStatus, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const startProfilesPolling = () => {
  profilesTimer = setInterval(fetchProfilesRealtime, 3000)
}

const stopProfilesPolling = () => {
  if (profilesTimer) {
    clearInterval(profilesTimer)
    profilesTimer = null
  }
}

const pollPrepareStatus = async () => {
  if (!taskId.value && !props.simulationId) return
  
  try {
    const res = await getPrepareStatus({
      task_id: taskId.value,
      simulation_id: props.simulationId
    })
    
    if (res.success && res.data) {
      const data = res.data
      
      // 更新进度
      prepareProgress.value = data.progress || 0
      progressMessage.value = data.message || ''
      
      // 解析阶段信息并输出详细日志
      if (data.progress_detail) {
        currentStage.value = data.progress_detail.current_stage_name || ''
        
        // 输出详细进度日志（避免重复）
        const detail = data.progress_detail
        const logKey = `${detail.current_stage}-${detail.current_item}-${detail.total_items}`
        if (logKey !== lastLoggedMessage && detail.item_description) {
          lastLoggedMessage = logKey
          const stageInfo = `[${detail.stage_index}/${detail.total_stages}]`
          if (detail.total_items > 0) {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.current_item}/${detail.total_items} - ${detail.item_description}`)
          } else {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.item_description}`)
          }
        }
      } else if (data.message) {
        // 从消息中提取阶段
        const match = data.message.match(/\[(\d+)\/(\d+)\]\s*([^:]+)/)
        if (match) {
          currentStage.value = match[3].trim()
        }
        // 输出消息日志（避免重复）
        if (data.message !== lastLoggedMessage) {
          lastLoggedMessage = data.message
          addLog(data.message)
        }
      }
      
      // 检查是否完成
      if (data.status === 'completed' || data.status === 'ready' || data.already_prepared) {
        addLog(t('log.prepareComplete'))
        stopPolling()
        stopProfilesPolling()
        await loadPreparedData()
      } else if (data.status === 'failed') {
        addLog(t('log.prepareFailedWithError', { error: data.error || t('common.unknownError') }))
        stopPolling()
        stopProfilesPolling()
      }
    }
  } catch (err) {
    console.warn('轮询状态失败:', err)
  }
}

const fetchProfilesRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    
    if (res.success && res.data) {
      const prevCount = profiles.value.length
      profiles.value = res.data.profiles || []
      // 只有当 API 返回有效值时才更新，避免覆盖已有的有效值
      if (res.data.total_expected) {
        expectedTotal.value = res.data.total_expected
      }
      
      // 提取实体类型
      const types = new Set()
      profiles.value.forEach(p => {
        if (p.entity_type) types.add(p.entity_type)
      })
      entityTypes.value = Array.from(types)
      
      // 输出 Profile 生成进度日志（仅当数量变化时）
      const currentCount = profiles.value.length
      if (currentCount > 0 && currentCount !== lastLoggedProfileCount) {
        lastLoggedProfileCount = currentCount
        const total = expectedTotal.value || '?'
        const latestProfile = profiles.value[currentCount - 1]
        const profileName = latestProfile?.name || latestProfile?.username || `Agent_${currentCount}`
        if (currentCount === 1) {
          addLog(t('log.startGeneratingAgentProfiles'))
        }
        addLog(t('log.agentProfile', { current: currentCount, total: total, name: profileName, profession: latestProfile?.profession || t('step2.unknownProfession') }))

        // 如果全部生成完成
        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(t('log.allProfilesComplete', { count: currentCount }))
        }
      }
    }
  } catch (err) {
    console.warn('获取 Profiles 失败:', err)
  }
}

// 配置轮询
const startConfigPolling = () => {
  configTimer = setInterval(fetchConfigRealtime, 2000)
}

const stopConfigPolling = () => {
  if (configTimer) {
    clearInterval(configTimer)
    configTimer = null
  }
}

const fetchConfigRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      // 输出配置生成阶段日志（避免重复）
      if (data.generation_stage && data.generation_stage !== lastLoggedConfigStage) {
        lastLoggedConfigStage = data.generation_stage
        if (data.generation_stage === 'generating_profiles') {
          addLog(t('log.generatingAgentProfileConfig'))
        } else if (data.generation_stage === 'generating_config') {
          addLog(t('log.generatingLLMConfig'))
        }
      }
      
      // 如果配置已生成
      if (data.config_generated && data.config) {
        simulationConfig.value = data.config
        addLog(t('log.configComplete'))

        // 显示详细配置摘要
        if (data.summary) {
          addLog(t('log.configSummaryAgents', { count: data.summary.total_agents }))
          addLog(t('log.configSummaryHours', { hours: data.summary.simulation_hours }))
          addLog(t('log.configSummaryPosts', { count: data.summary.initial_posts_count }))
          addLog(t('log.configSummaryTopics', { count: data.summary.hot_topics_count }))
          addLog(t('log.configSummaryPlatforms', { twitter: data.summary.has_twitter_config ? '✓' : '✗', reddit: data.summary.has_reddit_config ? '✓' : '✗' }))
        }
        
        // 显示时间配置详情
        if (data.config.time_config) {
          const tc = data.config.time_config
          addLog(t('log.timeConfigDetail', { minutes: tc.minutes_per_round, rounds: Math.floor((tc.total_simulation_hours * 60) / tc.minutes_per_round) }))
        }
        
        // 显示事件配置
        if (data.config.event_config?.narrative_direction) {
          const narrative = data.config.event_config.narrative_direction
          addLog(t('log.narrativeDirection', { direction: narrative.length > 50 ? narrative.substring(0, 50) + '...' : narrative }))
        }
        
        stopConfigPolling()
        phase.value = 4
        addLog(t('log.envSetupComplete'))
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('获取 Config 失败:', err)
  }
}

const loadPreparedData = async () => {
  phase.value = 2
  addLog(t('log.loadingExistingConfig'))

  // 最后获取一次 Profiles
  await fetchProfilesRealtime()
  addLog(t('log.loadedAgentProfiles', { count: profiles.value.length }))

  // 获取配置（使用实时接口）
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      if (res.data.config_generated && res.data.config) {
        simulationConfig.value = res.data.config
        addLog(t('log.configLoadSuccess'))

        // 显示详细配置摘要
        if (res.data.summary) {
          addLog(t('log.configSummaryAgents', { count: res.data.summary.total_agents }))
          addLog(t('log.configSummaryHours', { hours: res.data.summary.simulation_hours }))
          addLog(t('log.configSummaryPostsAlt', { count: res.data.summary.initial_posts_count }))
        }

        addLog(t('log.envSetupComplete'))
        phase.value = 4
        emit('update-status', 'completed')
      } else {
        // 配置尚未生成，开始轮询
        addLog(t('log.configGenerating'))
        startConfigPolling()
      }
    }
  } catch (err) {
    addLog(t('log.loadConfigFailed', { error: err.message }))
    emit('update-status', 'error')
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

// Nemotron 필터 선택지(facets) 로드. 풀이 있으면 조건 필터 UI 노출.
const fetchFacets = async () => {
  try {
    const res = await getNemotronFacets()
    if (res.success && res.data?.available) {
      facets.value = res.data
      // 범주형 필드별 선택 배열 초기화
      for (const k of Object.keys(res.data.fields || {})) {
        if (res.data.fields[k].type === 'categorical') selectedFilters[k] = []
      }
      if (res.data.fields?.age) {
        ageMin.value = res.data.fields.age.min
        ageMax.value = res.data.fields.age.max
      }
    }
  } catch (e) { /* 풀 없거나 실패 → 전체 랜덤만 */ }
}

onMounted(() => {
  // 그래프 엔티티 수를 가져와 추천값 세팅. 실제 생성은 사용자가 버튼 클릭 시.
  if (props.simulationId) {
    addLog(t('log.step2Init'))
    fetchEntityCount()
  }
  fetchFacets()
})

onUnmounted(() => {
  stopPolling()
  stopProfilesPolling()
  stopConfigPolling()
  if (countTimer) clearTimeout(countTimer)
})
</script>

<style scoped>
.env-setup-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--canvas-subdued);
  font-family: var(--font-sans);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Step Card */
.step-card {
  background: var(--surface-1);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  transition: all var(--motion-base) ease;
  position: relative;
}

.step-card.active {
  border-color: var(--primary);
  box-shadow: var(--shadow-card);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--ink-subdued);
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: var(--ink);
}

.step-title {
  font-weight: 600;
  font-size: var(--fs-section);
}

.badge {
  font-size: var(--fs-label);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-weight: 700;
  text-transform: uppercase;
}

.badge.success { background: var(--status-running-bg); color: var(--status-running); }
.badge.processing { background: var(--status-provisioning-bg); color: var(--status-provisioning); }
.badge.pending { background: var(--surface-2); color: var(--ink-subdued); }
.badge.accent { background: var(--status-provisioning-bg); color: var(--link); }

.card-content {
  /* No extra padding - uses step-card's padding */
}

.api-note {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-subdued);
  margin-bottom: 8px;
}

.description {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Action Section */
.action-section {
  margin-top: 16px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: var(--fs-body);
  font-weight: 700;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--motion-base) ease;
}

.action-btn.primary {
  background: var(--primary);
  color: var(--on-primary);
}

.action-btn.primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.action-btn.secondary {
  background: var(--surface-1);
  color: var(--ink);
  border-color: var(--border);
}

.action-btn.secondary:hover:not(:disabled) {
  background: var(--surface-2);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-group {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-group.dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.action-group.dual .action-btn {
  width: 100%;
}

/* Info Card */
.info-card {
  background: var(--surface-2);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-top: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: var(--fs-label);
  color: var(--ink-muted);
}

.info-value {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--ink);
}

.info-value.mono {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  background: var(--surface-2);
  padding: 16px;
  border-radius: var(--radius-md);
}

.stat-card {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: var(--fs-display);
  font-weight: 700;
  color: var(--ink);
  font-family: var(--font-mono);
}

.stat-label {
  font-size: 11px;
  color: var(--ink-subdued);
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

/* Profiles Preview */
.profiles-preview {
  margin-top: 20px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.profiles-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.profiles-list::-webkit-scrollbar {
  width: 4px;
}

.profiles-list::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: var(--radius-sm);
}

.profiles-list::-webkit-scrollbar-thumb:hover {
  background: var(--ink-subdued);
}

.profile-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: all var(--motion-base) ease;
}

.profile-card:hover {
  border-color: var(--ink-subdued);
  background: var(--surface-1);
}

.profile-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.profile-realname {
  font-size: var(--fs-body);
  font-weight: 700;
  color: var(--ink);
}

.profile-username {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-subdued);
}

.profile-meta {
  margin-bottom: 8px;
}

.profile-profession {
  font-size: 11px;
  color: var(--ink-muted);
  background: var(--surface-2);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.profile-bio {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  line-height: 1.6;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic-tag {
  font-size: 10px;
  color: var(--link);
  background: var(--status-provisioning-bg);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.topic-more {
  font-size: 10px;
  color: var(--ink-subdued);
  padding: 2px 6px;
}

/* Config Preview */
/* Config Detail Panel */
.config-detail-panel {
  margin-top: 16px;
}

.config-block {
  margin-top: 16px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.config-block:first-child {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.config-block-title {
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.config-block-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--surface-2);
  color: var(--ink-muted);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.config-item {
  background: var(--surface-2);
  padding: 12px 14px;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item-label {
  font-size: 11px;
  color: var(--ink-subdued);
}

.config-item-value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

/* Time Periods */
.time-periods {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.period-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--surface-2);
  border-radius: var(--radius-md);
}

.period-label {
  font-size: var(--fs-label);
  font-weight: 500;
  color: var(--ink-muted);
  min-width: 70px;
}

.period-hours {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-muted);
  flex: 1;
}

.period-multiplier {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--link);
  background: var(--status-provisioning-bg);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

/* Agents Cards */
.agents-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.agents-cards::-webkit-scrollbar {
  width: 4px;
}

.agents-cards::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: var(--radius-sm);
}

.agents-cards::-webkit-scrollbar-thumb:hover {
  background: var(--ink-subdued);
}

.agent-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  transition: all var(--motion-base) ease;
}

.agent-card:hover {
  border-color: var(--ink-subdued);
  background: var(--surface-1);
}

/* Agent Card Header */
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.agent-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-id {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-subdued);
}

.agent-name {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--ink);
}

.agent-tags {
  display: flex;
  gap: 6px;
}

.agent-type {
  font-size: 10px;
  color: var(--ink-muted);
  background: var(--surface-2);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.agent-stance {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.stance-neutral {
  background: var(--surface-2);
  color: var(--ink-muted);
}

.stance-supportive {
  background: var(--status-running-bg);
  color: var(--status-running);
}

.stance-opposing {
  background: var(--status-stopped-bg);
  color: var(--status-stopped);
}

.stance-observer {
  background: var(--status-pending-bg);
  color: var(--status-pending);
}

/* Agent Timeline */
.agent-timeline {
  margin-bottom: 14px;
}

.timeline-label {
  display: block;
  font-size: 10px;
  color: var(--ink-subdued);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mini-timeline {
  display: flex;
  gap: 2px;
  height: 16px;
  background: var(--surface-2);
  border-radius: var(--radius-md);
  padding: 3px;
}

.timeline-hour {
  flex: 1;
  background: var(--border);
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.timeline-hour.active {
  background: var(--link);
}

.timeline-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--ink-subdued);
}

/* Agent Params */
.agent-params {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.param-item .param-label {
  font-size: 10px;
  color: var(--ink-subdued);
}

.param-item .param-value {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-muted);
}

.param-value.with-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-bar {
  height: 4px;
  background: var(--link);
  border-radius: var(--radius-sm);
  min-width: 4px;
  max-width: 40px;
}

.param-value.positive {
  color: var(--status-running);
}

.param-value.negative {
  color: var(--status-stopped);
}

.param-value.neutral {
  color: var(--ink-muted);
}

.param-value.highlight {
  color: var(--link);
}

/* Platforms Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.platform-card {
  background: var(--surface-2);
  padding: 14px;
  border-radius: var(--radius-md);
}

.platform-card-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.platform-name {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--ink);
}

.platform-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: var(--fs-label);
  color: var(--ink-muted);
}

.param-value {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

/* Reasoning Content */
.reasoning-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reasoning-item {
  padding: 12px 14px;
  background: var(--surface-2);
  border-radius: var(--radius-md);
}

.reasoning-text {
  font-size: var(--fs-body);
  color: var(--ink-muted);
  line-height: 1.7;
  margin: 0;
}

/* Profile Modal */
.profile-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.profile-modal {
  background: var(--surface-1);
  border-radius: var(--radius-md);
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-modal);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background: var(--surface-1);
  border-bottom: 1px solid var(--border);
}

.modal-header-info {
  flex: 1;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.modal-realname {
  font-size: var(--fs-title);
  font-weight: 700;
  color: var(--ink);
}

.modal-username {
  font-family: var(--font-mono);
  font-size: var(--fs-body);
  color: var(--ink-subdued);
}

.modal-profession {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  background: var(--surface-2);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  display: inline-block;
  font-weight: 500;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: var(--ink-subdued);
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.2s;
  padding: 0;
}

.close-btn:hover {
  color: var(--ink);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 基本信息网格 */
.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px 16px;
  margin-bottom: 32px;
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: var(--ink-subdued);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-weight: 700;
}

.info-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.info-value.mbti {
  font-family: var(--font-mono);
  color: var(--link);
}

/* 模块区域 */
.modal-section {
  margin-bottom: 28px;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-subdued);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.section-bio {
  font-size: 14px;
  color: var(--ink);
  line-height: 1.6;
  margin: 0;
  padding: 16px;
  background: var(--surface-2);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--border);
}

/* 话题标签 */
.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-item {
  font-size: 11px;
  color: var(--link);
  background: var(--status-provisioning-bg);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  transition: all 0.2s;
  border: none;
}

.topic-item.skill-item {
  color: var(--status-running);
  background: var(--status-running-bg);
}

.agent-count-setup {
  margin-top: 12px;
  padding: 14px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.agent-count-setup .count-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.agent-count-setup .count-label {
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
}
.agent-count-setup .count-input {
  width: 100px;
  padding: 6px 10px;
  font-size: var(--fs-body);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  outline: none;
  background: var(--surface-1);
  color: var(--ink);
}
.agent-count-setup .count-input:focus {
  border-color: var(--link);
}
.agent-count-setup .count-hint {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}
.agent-count-setup .generate-btn {
  align-self: flex-start;
  padding: 8px 18px;
  font-size: var(--fs-body);
  font-weight: 700;
  color: var(--on-primary);
  background: var(--primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--motion-base);
}
.agent-count-setup .generate-btn:hover {
  background: var(--primary-hover);
}
.agent-count-setup .generate-btn:disabled {
  background: var(--border);
  color: var(--ink-subdued);
  cursor: not-allowed;
}

/* ===== 샘플링 방식 + 조건 필터 ===== */
.sampling-mode {
  display: flex;
  align-items: center;
  gap: 12px;
  border-top: 1px dashed var(--border);
  padding-top: 12px;
}
.sampling-mode .mode-title {
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
}
.mode-tabs {
  display: inline-flex;
  background: var(--surface-2);
  border-radius: var(--radius-md);
  padding: 3px;
  gap: 2px;
}
.mode-tab {
  padding: 6px 14px;
  font-size: var(--fs-label);
  font-weight: 600;
  color: var(--ink-muted);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s;
}
.mode-tab.active {
  background: var(--surface-1);
  color: var(--link);
  box-shadow: var(--shadow-card);
}

.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}
.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-group-title {
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.filter-group-title.age-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  text-transform: none;
}
.filter-group-count {
  font-size: 10px;
  font-weight: 700;
  color: var(--on-primary);
  background: var(--link);
  min-width: 16px;
  height: 16px;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 120px;
  overflow-y: auto;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: var(--fs-label);
  color: var(--ink-muted);
  background: var(--surface-2);
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all 0.15s;
}
.filter-chip:hover {
  background: var(--status-provisioning-bg);
}
.filter-chip.selected {
  color: var(--link-hover);
  background: var(--status-provisioning-bg);
  border-color: var(--link);
  font-weight: 600;
}
.filter-chip .chip-count {
  font-size: 10px;
  color: var(--ink-subdued);
  font-family: var(--font-mono);
}
.filter-chip.selected .chip-count {
  color: var(--link);
}
.age-range-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.age-input {
  width: 68px;
  padding: 5px 8px;
  font-size: var(--fs-body);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  outline: none;
  background: var(--surface-1);
  color: var(--ink);
}
.age-input:focus { border-color: var(--link); }
.age-sep { color: var(--ink-subdued); }
.age-unit { font-size: var(--fs-label); color: var(--ink-subdued); }

.filter-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  font-size: var(--fs-label);
  color: var(--status-running);
  background: var(--status-running-bg);
  border-radius: var(--radius-md);
}
.filter-preview.warn {
  color: var(--status-stopped);
  background: var(--status-stopped-bg);
}
.filter-preview .preview-text { flex: 1; }
.filter-clear {
  font-size: 11px;
  color: var(--ink-muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 3px 8px;
  cursor: pointer;
  white-space: nowrap;
}
.filter-clear:hover {
  background: var(--surface-1);
  color: var(--ink);
}

.topic-item:hover {
  background: var(--status-provisioning-bg);
  color: var(--link-hover);
}

/* 详细人设 */
.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.dimension-card {
  background: var(--surface-2);
  padding: 12px;
  border-radius: var(--radius-md);
  border-left: 3px solid var(--border);
  transition: all 0.2s;
}

.dimension-card:hover {
  background: var(--surface-2);
  border-left-color: var(--ink-subdued);
}

.dim-title {
  display: block;
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 4px;
}

.dim-desc {
  display: block;
  font-size: 10px;
  color: var(--ink-subdued);
  line-height: 1.4;
}

.persona-content {
  max-height: none;
  overflow: visible;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.persona-content::-webkit-scrollbar {
  width: 4px;
}

.persona-content::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: var(--radius-sm);
}

.section-persona {
  font-size: var(--fs-body);
  color: var(--ink-muted);
  line-height: 1.8;
  margin: 0;
  text-align: justify;
}

/* System Logs */
.system-logs {
  background: var(--nav-bg);
  color: var(--nav-ink-inactive);
  padding: 16px;
  font-family: var(--font-mono);
  border-top: 1px solid var(--nav-bg-2);
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--nav-bg-2);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: var(--nav-ink-inactive);
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px; /* Approx 4 lines visible */
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: var(--nav-bg-2);
  border-radius: var(--radius-sm);
}

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time {
  color: var(--nav-ink-inactive);
  min-width: 75px;
}

.log-msg {
  color: var(--nav-ink);
  word-break: break-all;
}

/* Spinner */
.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
/* Orchestration Content */
.orchestration-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 16px;
}

.box-label {
  display: block;
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.narrative-box {
  background: var(--surface-1);
  padding: 20px 24px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
  transition: all 0.3s ease;
}

.narrative-box .box-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink-muted);
  font-size: var(--fs-body);
  margin-bottom: 12px;
  font-weight: 600;
}

.special-icon {
  filter: drop-shadow(0 2px 4px rgba(255, 153, 0, 0.25));
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.narrative-box:hover .special-icon {
  transform: rotate(180deg);
}

.narrative-text {
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--ink);
  line-height: 1.8;
  margin: 0;
  text-align: justify;
  letter-spacing: 0.01em;
}

.topics-section {
  background: var(--surface-1);
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-topic-tag {
  font-size: var(--fs-label);
  color: var(--link);
  background: var(--status-provisioning-bg);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-weight: 500;
}

.hot-topic-more {
  font-size: 11px;
  color: var(--ink-subdued);
  padding: 4px 6px;
}

.initial-posts-section {
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-left: 8px;
  border-left: 2px solid var(--border);
  margin-top: 12px;
}

.timeline-item {
  position: relative;
  padding-left: 20px;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 14px;
  width: 12px;
  height: 2px;
  background: var(--border);
}

.timeline-content {
  background: var(--surface-2);
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.post-role {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink);
  text-transform: uppercase;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-id,
.post-username {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-muted);
  line-height: 1;
  vertical-align: baseline;
}

.post-username {
  margin-right: 6px;
}

.post-text {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  line-height: 1.5;
  margin: 0;
}

/* 模拟轮数配置样式 */
.rounds-config-section {
  margin: 24px 0;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: var(--fs-section);
  font-weight: 600;
  color: var(--ink);
}

.section-desc {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}

.desc-highlight {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--ink);
  background: var(--surface-2);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  margin: 0 2px;
}

/* Switch Control */
.switch-control {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-pill);
  transition: background 0.2s;
}

.switch-control:hover {
  background: var(--surface-2);
}

.switch-control input {
  display: none;
}

.switch-track {
  width: 36px;
  height: 20px;
  background: var(--border);
  border-radius: var(--radius-pill);
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-track::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: var(--surface-1);
  border-radius: 50%;
  box-shadow: var(--shadow-card);
  transition: transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-control input:checked + .switch-track {
  background: var(--link);
}

.switch-control input:checked + .switch-track::after {
  transform: translateX(16px);
}

.switch-label {
  font-size: var(--fs-label);
  font-weight: 500;
  color: var(--ink-muted);
}

.switch-control input:checked ~ .switch-label {
  color: var(--ink);
}

/* Slider Content */
.rounds-content {
  animation: fadeIn 0.3s ease;
}

.slider-display {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.slider-main-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.val-num {
  font-family: var(--font-mono);
  font-size: var(--fs-display);
  font-weight: 700;
  color: var(--ink);
}

.val-unit {
  font-size: var(--fs-label);
  color: var(--ink-muted);
  font-weight: 500;
}

.slider-meta-info {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-muted);
  background: var(--surface-2);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.range-wrapper {
  position: relative;
  padding: 0 2px;
}

.minimal-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  background: var(--border);
  border-radius: var(--radius-sm);
  outline: none;
  background-image: linear-gradient(var(--link), var(--link));
  background-size: var(--percent, 0%) 100%;
  background-repeat: no-repeat;
  cursor: pointer;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--surface-1);
  border: 2px solid var(--link);
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: transform 0.1s;
  margin-top: -6px; /* Center thumb */
}

.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.minimal-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: var(--radius-sm);
}

.range-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-subdued);
  position: relative;
}

.mark-recommend {
  cursor: pointer;
  transition: color 0.2s;
  position: relative;
}

.mark-recommend:hover {
  color: var(--link);
}

.mark-recommend.active {
  color: var(--link);
  font-weight: 600;
}

.mark-recommend::after {
  content: '';
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 1px;
  height: 4px;
  background: var(--border);
}

/* Auto Info */
.auto-info-card {
  display: flex;
  align-items: center;
  gap: 24px;
  background: var(--surface-2);
  padding: 16px 20px;
  border-radius: var(--radius-md);
}

.auto-value {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4px;
  padding-right: 24px;
  border-right: 1px solid var(--border);
}

.auto-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.auto-meta-row {
  display: flex;
  align-items: center;
}

.duration-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--ink-muted);
  background: var(--surface-1);
  border: 1px solid var(--border);
  padding: 3px 8px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.auto-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.auto-desc p {
  margin: 0;
  font-size: var(--fs-body);
  color: var(--ink-muted);
  line-height: 1.5;
}

.highlight-tip {
  margin-top: 4px !important;
  font-size: var(--fs-label) !important;
  color: var(--link) !important;
  font-weight: 500;
  cursor: pointer;
}

.highlight-tip:hover {
  text-decoration: underline;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .profile-modal {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-leave-active .profile-modal {
  transition: all 0.3s ease-in;
}

.modal-enter-from .profile-modal,
.modal-leave-to .profile-modal {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
