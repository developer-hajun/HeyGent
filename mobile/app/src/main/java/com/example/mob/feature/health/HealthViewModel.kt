package com.heygents.mob.feature.health

import android.app.Activity
import android.content.Context
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.heygents.mob.data.repository.HealthRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class HealthViewModel(context: Context) : ViewModel() {

    sealed interface HealthSyncState {
        data object Idle : HealthSyncState
        data object Loading : HealthSyncState
        data object Success : HealthSyncState
        data class Error(val message: String) : HealthSyncState
    }

    private val repository = HealthRepository(context)

    private val _syncState = MutableStateFlow<HealthSyncState>(HealthSyncState.Idle)
    val syncState: StateFlow<HealthSyncState> = _syncState

    val permissions = repository.permissions

    fun requestPermissions(activity: Activity) {
        viewModelScope.launch {
            repository.connect()
            repository.requestPermissions(activity)
        }
    }

    fun syncWatchData() {
        viewModelScope.launch {
            Log.d("HealthSync", "데이터 동기화 프로세스 시작")
            
            repository.connect()
            if (!repository.hasAllPermissions()) {
                Log.w("HealthSync", "권한이 없습니다. 동기화를 건너뜁니다.")
                _syncState.value = HealthSyncState.Error("삼성 헬스 권한이 필요합니다.")
                return@launch
            }

            _syncState.value = HealthSyncState.Loading
            repository.syncToServer().fold(
                onSuccess = {
                    Log.d("HealthSync", "데이터 동기화 성공")
                    _syncState.value = HealthSyncState.Success
                },
                onFailure = {
                    Log.e("HealthSync", "데이터 동기화 실패: ${it.message}", it)
                    _syncState.value = HealthSyncState.Error(it.message ?: "알 수 없는 오류")
                }
            )
        }
    }

    private var periodicSyncJob: Job? = null

    // TODO: 테스트용 - 30초마다 데이터 수집. 실제 배포 전 제거 필요
    fun startPeriodicSync() {
        if (periodicSyncJob?.isActive == true) return
        Log.d("HealthSync", "주기적 동기화 시작 (30초 간격)")
        periodicSyncJob = viewModelScope.launch {
            while (true) {
                syncWatchData()
                delay(30_000L)
            }
        }
    }

    fun stopPeriodicSync() {
        periodicSyncJob?.cancel()
        periodicSyncJob = null
    }

    override fun onCleared() {
        super.onCleared()
        stopPeriodicSync()
    }
}
