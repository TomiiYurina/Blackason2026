import { useEffect, useRef, useState } from 'react'
import './App.css'
import * as mobilenet from '@tensorflow-models/mobilenet'
import * as knnClassifier from '@tensorflow-models/knn-classifier'
import * as tf from '@tensorflow/tfjs'

function App() {
  const getTodayPaidCount = () => {
    const stampRaw = localStorage.getItem('blackthunderTaxStampDate')
    if (!stampRaw) return 0;
    try {
      const stamp = JSON.parse(stampRaw)
      if (stamp.date.split('T')[0] === new Date().toISOString().split('T')[0]) {
        return stamp.count || 0;
      }
    } catch(e) {}
    return 0;
  }

  const [supported, setSupported] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)
  const [captured, setCaptured] = useState(false)
  const [modelReady, setModelReady] = useState(false)
  const [tmReady, setTmReady] = useState(false)
  const [modelStatus, setModelStatus] = useState('未読み込み')
  const [loadingModel, setLoadingModel] = useState(false)
  const [batchActive, setBatchActive] = useState(false)
  const [isCameraActive, setIsCameraActive] = useState(false)
  const [totalRequired] = useState(parseInt(localStorage.getItem('final_tax_to_pay') || '1', 10))
  const [paidCount, setPaidCount] = useState(getTodayPaidCount())
  
  // ザクザク音の再生関数を追加
  const playCrunchSound = () => {
    try {
      const audio = new Audio('../3939.mp3')
      audio.volume = 1.0
      audio.play()
    } catch (e) {
      console.error(e)
    }
  }
  const [batchProgress, setBatchProgress] = useState(0)
  const [batchTarget, setBatchTarget] = useState(5)
  const [result, setResult] = useState('まだ判定されていません。')
  const [taunt, setTaunt] = useState('')
  const [message, setMessage] = useState('カメラを開始してキャプチャしてください。')
  const [error, setError] = useState('')
  const [bagExamples, setBagExamples] = useState(0)
  const [noneExamples, setNoneExamples] = useState(0)
  const [showFullScreenVideo, setShowFullScreenVideo] = useState(false)
  const batchTimerRef = useRef(null)

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const overlayVideoRef = useRef(null)
  const overlayVideoSrc = `${import.meta.env.BASE_URL}media/nouzeikanryou_sound.mp4`
  const streamRef = useRef(null)
  const classifierRef = useRef(null)
  const mobileNetRef = useRef(null)
  const samplesRef = useRef([])
  const tmModelRef = useRef(null)
  const tmLabelsRef = useRef(['bag', 'none'])
  const tmInputSizeRef = useRef(224)
  const TAX_STAMP_DATE_KEY = 'blackthunderTaxStampDate'


  

const loadModel = async () => {
    if (mobileNetRef.current && classifierRef.current && tmModelRef.current) {
      return
    }

    setLoadingModel(true)
    setMessage('モデルを読み込んでいます...')
    setError('')

    if (!classifierRef.current) {
      classifierRef.current = knnClassifier.create()
    }

    if (mobileNetRef.current && classifierRef.current && !tmModelRef.current) {
      try {
        await loadTMModel()
        if (tmModelRef.current) setTmReady(true)
      } catch (e) {
        console.warn('TM load failed during reload', e)
      }
      setLoadingModel(false)
      return
    }

    try {
      mobileNetRef.current = await mobilenet.load({ version: 2, alpha: 0.75 })
      // Teachable Machine モデルも読み込んでおく（あれば）
      try {
        await loadTMModel()
      } catch (e) {
        // TM がなくても続行
      }

      setModelReady(true)
      setTmReady(Boolean(tmModelRef.current))
      setModelStatus('準備完了')
      setLoadingModel(false)
      setMessage('モデル準備完了です。まずはサンプルを追加してください。')
    } catch (err) {
      setModelStatus('エラー')
      setError(err instanceof Error ? err.message : 'モデルの読み込みに失敗しました')
      setModelStatus('読み込み失敗')
      setMessage('モデルの読み込みに失敗しました。再読み込みしてください。')
      setModelReady(false)
      setLoadingModel(false)
    }
  }

  // Teachable Machine のモデルを読み込む（public/models/tm_model を期待）
  const loadTMModel = async () => {
    const metadataPath = './models/tm_model/metadata.json'
    const modelPath = './models/tm_model/model.json'

    try {
      const metaResp = await fetch(metadataPath)
      if (metaResp.ok) {
        const meta = await metaResp.json()
        if (Array.isArray(meta.labels)) tmLabelsRef.current = meta.labels
        if (meta.input_shape && Array.isArray(meta.input_shape)) {
          // input_shape may be like [null, h, w, c]
          tmInputSizeRef.current = meta.input_shape[1] || tmInputSizeRef.current
        }
        if (meta.image_size) tmInputSizeRef.current = meta.image_size
      }
    } catch (e) {
      // メタ情報が無くても問題なし
    }

    try {
      tmModelRef.current = await tf.loadLayersModel(modelPath)
      setTmReady(true)
      setMessage('Teachable Machine モデル読み込み完了')
    } catch (e) {
      setTmReady(false)
      setError(`TMモデルの読み込みに失敗しました: ${e instanceof Error ? e.message : String(e)}`)
      setMessage('TMモデルの読み込みに失敗しました。モデル再読み込みを押してください。')
      console.warn('TM load failed', e)
    }
  }

  useEffect(() => {
    const hasCamera = Boolean(navigator.mediaDevices?.getUserMedia)
    setSupported(hasCamera)
    if (hasCamera) loadModel()
  }, [])


  const stopCamera = () => {
    playCrunchSound()
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    setCameraOn(false)
    setMessage('カメラを停止しました。再び開始するには「カメラ開始」を押してください。')
    setCaptured(false)
    setResult('まだ判定されていません。')
  }

  const startCamera = async () => {
    playCrunchSound()
    setError('')
    setMessage('カメラを起動しています…')
    setResult('まだ判定されていません。')
    setTaunt('')
    setCaptured(false)

    try {
      if (!modelReady && !loadingModel) {
        await loadModel()
      }
      if (!tmReady && !loadingModel) {
        await loadTMModel()
      }
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      setCameraOn(true)
      if (!modelReady || !tmReady) {
        setMessage('カメラ接続はできましたが、モデルが準備できていません。まずは「モデル再読み込み」を押してください。')
      } else {
        setMessage('袋をカメラに写してキャプチャしてください。')
      }
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
    } catch (err) {
      const nextMessage = err instanceof Error ? err.message : 'カメラにアクセスできませんでした'
      setError(nextMessage)
      setMessage('カメラを開始できませんでした。')
      setCameraOn(false)
    }
  }

  const playFullScreenVideo = async () => {
    if (!overlayVideoRef.current) return
    setShowFullScreenVideo(true)
    overlayVideoRef.current.currentTime = 0
    try {
      await overlayVideoRef.current.play()
    } catch (err) {
      console.warn('動画再生に失敗しました', err)
    }
  }

  const hideFullScreenVideo = () => {
    if (overlayVideoRef.current) {
      overlayVideoRef.current.pause()
      overlayVideoRef.current.currentTime = 0
    }
    setShowFullScreenVideo(false)
  }

  const handleOverlayVideoEnded = () => {
    setShowFullScreenVideo(false)
    // スタンプ記録を保存（個数も一緒に）
    const todayISO = new Date().toISOString()
    const newPaidCount = paidCount + 1
    localStorage.setItem(TAX_STAMP_DATE_KEY, JSON.stringify({ date: todayISO, count: newPaidCount }))
    setPaidCount(newPaidCount)
    
    // 1個判定したら、まずは完了画面へ遷移してカレンダーに戻らせる
    window.location.href = '../nouzeizumi.html'
  }

  const addSample = async (label) => {
    if (!videoRef.current || !canvasRef.current) {
      setError('ビデオストリームが利用できません。')
      return
    }

    if (!loadingModel && !modelReady) {
      setMessage('モデルが未準備です。自動で読み込みを開始します。しばらくお待ちください。')
      await loadModel()
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      setError('キャンバスの初期化に失敗しました。')
      return
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const imageData = canvas.toDataURL('image/png')
    samplesRef.current.push({ label, image: imageData })

    if (modelReady && mobileNetRef.current && classifierRef.current) {
      const activation = mobileNetRef.current.infer(video, true)
      classifierRef.current.addExample(activation, label)
    }

    if (label === 'bag') {
      setBagExamples((count) => count + 1)
      setMessage(modelReady ? 'ブラックサンダー袋のサンプルを追加しました。' : 'ブラックサンダー袋のサンプルを保存しました。')
    } else {
      setNoneExamples((count) => count + 1)
      setMessage(modelReady ? '袋ではないサンプルを追加しました。' : '袋ではないサンプルを保存しました。')
    }
  }

  const startBatchSample = async (label) => {
    if (!videoRef.current || !canvasRef.current) {
      setError('ビデオストリームが利用できません。')
      return
    }

    if (!loadingModel && !modelReady) {
      setMessage('モデル未準備ですが、連続サンプルを開始します。モデルの読み込みも試行します。')
      await loadModel()
    }
    if (loadingModel) {
      setMessage('モデルを読み込んでいます。連続サンプルはサンプル保存として進行します。')
    }

    setBatchActive(true)
    setBatchProgress(0)
    setMessage(`連続サンプルを開始します。${batchTarget}枚の${label === 'bag' ? '袋' : '袋以外'}を撮影します。`)

    const captureNext = async (count) => {
      if (!videoRef.current || !canvasRef.current) {
        setError('連続撮影中にビデオが使えませんでした。')
        setBatchActive(false)
        return
      }

      const video = videoRef.current
      const canvas = canvasRef.current
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        setError('連続撮影中にキャンバスの初期化に失敗しました。')
        setBatchActive(false)
        return
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const imageData = canvas.toDataURL('image/png')
      samplesRef.current.push({ label, image: imageData })

      if (modelReady && mobileNetRef.current && classifierRef.current) {
        const activation = mobileNetRef.current.infer(video, true)
        classifierRef.current.addExample(activation, label)
      }

      if (label === 'bag') {
        setBagExamples((prev) => prev + 1)
      } else {
        setNoneExamples((prev) => prev + 1)
      }
      setBatchProgress(count + 1)
      setMessage(`連続サンプル中: ${count + 1}/${batchTarget}`)

      if (count + 1 >= batchTarget) {
        setBatchActive(false)
        setMessage(`連続サンプルが完了しました。${batchTarget}枚保存されました。`) 
        return
      }

      batchTimerRef.current = window.setTimeout(() => captureNext(count + 1), 800)
    }

    captureNext(0)
  }

  const stopBatchSample = () => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current)
      batchTimerRef.current = null
    }
    setBatchActive(false)
    setMessage('連続サンプルを中止しました。')
  }

  const captureFrame = async () => {
    if (!videoRef.current || !canvasRef.current) {
      setError('ビデオストリームが利用できません。')
      return
    }

    // モデル未準備なら自動で読み込みを試みるが、キャプチャ自体は行う
    if (!loadingModel && !modelReady) {
      setMessage('モデルが未準備です。自動で読み込みを開始します。しばらくお待ちください。')
      loadModel().catch(() => {})
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      setError('キャンバスの初期化に失敗しました。')
      return
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    setCaptured(true)
    // 画像を保存
    samplesRef.current.push({ label: 'capture', image: canvas.toDataURL('image/png') })

    if (modelReady && !loadingModel) {
      setMessage('画像をキャプチャしました。判定を実行します。')
      await runBagDetection()
    } else {
      setMessage('画像をキャプチャしました（保存のみ）。モデルが準備できていないため判定は行いません。モデル再読み込みを行ってください。')
    }
  }

  const predictWithTM = async (canvas) => {
    if (!tmModelRef.current) throw new Error('TMモデルが読み込まれていません')
    const inputSize = tmInputSizeRef.current || 224
    let img = tf.browser.fromPixels(canvas).resizeNearestNeighbor([inputSize, inputSize]).toFloat()
    img = img.div(127.5).sub(1).expandDims(0)
    const predsTensor = await tmModelRef.current.predict(img)
    const preds = await predsTensor.data()
    if (predsTensor.dispose) predsTensor.dispose()
    img.dispose()
    const maxIdx = preds.indexOf(Math.max(...preds))
    return { label: tmLabelsRef.current[maxIdx] || String(maxIdx), confidence: preds[maxIdx] }
  }

  const runBagDetection = async () => {
    playCrunchSound()
    // まず Teachable Machine モデルで予測を試す（あれば）
    if (tmModelRef.current && canvasRef.current) {
      try {
        const res = await predictWithTM(canvasRef.current)
        const isBag = res.label === 'sample' || res.label === 'bag'
        if (isBag) {
          setResult('ブラックサンダーです！')
          setTaunt('')
          setMessage('判定完了（Teachable Machine）')
          playFullScreenVideo()
        } else {
          setResult('ブラックサンダーが見つかりませんでした。')
          const taunts = [
            "バグは直らなくても、ブラックサンダーは裏切らないよ？",
            "コンパイル待ちのスキマ時間、ブラックサンダーかじりませんか？",
            "噛みごたえのある糖分も必要じゃない？"
          ]
          setTaunt(taunts[Math.floor(Math.random() * taunts.length)])
          setMessage('判定完了（Teachable Machine）')
          hideFullScreenVideo()
        }
        return
      } catch (e) {
        console.warn('TM predict failed, falling back to KNN', e)
      }
    }

    if (!mobileNetRef.current || !classifierRef.current || !videoRef.current) {
      setError('モデルまたはビデオが準備できていません。')
      return
    }
    if (classifierRef.current.getNumClasses() === 0) {
      setError('まずはサンプルを追加してください。')
      return
    }

    try {
      const activation = mobileNetRef.current.infer(videoRef.current, true)
      const prediction = await classifierRef.current.predictClass(activation)
      const isBag = prediction.label === 'bag' || prediction.label === 'sample'
      
      if (isBag) {
        setResult('ブラックサンダーです！')
        setTaunt('')
        setMessage('判定完了です。')
        playFullScreenVideo()
      } else {
        setResult('ブラックサンダーが見つかりませんでした。')
        const taunts = [
          "バグは直らなくても、ブラックサンダーは裏切らないよ？",
          "コンパイル待ちのスキマ時間、ブラックサンダーかじりませんか？",
          "噛みごたえのある糖分も必要じゃない？"
        ]
        setTaunt(taunts[Math.floor(Math.random() * taunts.length)])
        setMessage('判定完了です。')
        hideFullScreenVideo()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '判定に失敗しました')
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-card">
        <h1>ブラックサンダー袋判定</h1>
        <p>Webカメラで袋を写して、学習した画像モデルで判定します。</p>
        
        <div className="quota-display" style={{ background: '#31160a', color: '#FDE11D', padding: '10px', borderRadius: '8px', marginBottom: '15px', fontWeight: 'bold', fontSize: '18px', textAlign: 'center' }}>
           本日のノルマ: {totalRequired}個中 {paidCount}個 納税済み
           {paidCount < totalRequired ? `（残り ${totalRequired - paidCount}個）` : '（完納！）'}
        </div>

        {!supported ? (
          <div className="message warning">このブラウザではカメラ入力が使えません。</div>
        ) : (
          <div className="controls camera-controls">
            <div className="button-row">
              <button type="button" className="primary" onClick={() => { playCrunchSound(); startCamera(); }} disabled={cameraOn}>
                カメラ開始
              </button>
              <button type="button" className="secondary" onClick={() => { playCrunchSound(); stopCamera(); }} disabled={!cameraOn}>
                カメラ停止
              </button>
            </div>

                  <div className="training-row">
              <button type="button" className="primary" onClick={() => { playCrunchSound(); captureFrame(); }} disabled={!cameraOn || batchActive}>
                キャプチャして判定
              </button>
              <button type="button" className="secondary" onClick={async () => { playCrunchSound(); setError(''); await loadModel(); await loadTMModel(); }} disabled={loadingModel || batchActive}>
                モデル再読み込み
              </button>
            </div>

            <div className="camera-grid">
              <div className="video-box">
                <video ref={videoRef} className="camera-video" muted playsInline />
                <div className="video-label">ライブ映像</div>
              </div>

              <div className="preview-box">
                <canvas ref={canvasRef} className="preview-canvas" />
                <div className="video-label">キャプチャ画像</div>
              </div>
            </div>

            <div className="status-box">
              <p className="status-label">判定結果</p>
              <div className={`message ${result === 'ブラックサンダーです！' ? 'success' : result === 'ブラックサンダーが見つかりませんでした。' ? 'error' : 'info'}`}>
                {result}
                {taunt && <div style={{ color: '#3D1C04', marginTop: '10px', fontSize: '1.05rem', fontWeight: 'bold' }}>{taunt}</div>}
              </div>
              {error && <div className="message error">{error}</div>}
            </div>

            <div className={`fullscreen-video-overlay ${showFullScreenVideo ? 'visible' : ''}`}>
              <video
                ref={overlayVideoRef}
                className="fullscreen-video"
                src={overlayVideoSrc}
                playsInline
                preload="auto"
                onEnded={handleOverlayVideoEnded}
              />
              <button type="button" className="close-overlay" onClick={() => { playCrunchSound(); hideFullScreenVideo(); }}>
                閉じる
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
